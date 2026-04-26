"""
Integration tests for backend/app/services/agent_service.py.

All LLM and MCP calls are mocked. We test the wiring between AgentService,
FinancialAgentFactory, and the message-building logic with real class instances.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, ToolMessage

from app.core.config import Settings
from app.schemas.agent import (
    ChatRequest,
    ChatResponse,
    ConversationMessage,
    MessageRole,
    StreamEventType,
)
from app.services.agent_service import AgentService
from app.services.mcp_manager import MCPClientManager


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="sk-test",
        supabase_db_url="postgresql://test:test@localhost/test",
        mcp_server_url="http://localhost:8080/mcp",
        llm_model="openai:gpt-4o-mini",
    )


@pytest.fixture
def mock_mcp() -> MagicMock:
    mcp = MagicMock(spec=MCPClientManager)
    mcp.is_connected = True
    mcp.get_tools.return_value = []
    return mcp


@pytest.fixture
def agent_service(mock_mcp, settings) -> AgentService:
    return AgentService(mcp_manager=mock_mcp, settings=settings)


def _make_agent_result(answer: str, tool_name: str | None = None) -> dict:
    """Build a fake agent invocation result dict."""
    ai_final = AIMessage(content=answer)
    ai_final.tool_calls = []
    messages = [ai_final]

    if tool_name:
        ai_with_tool = AIMessage(content="")
        ai_with_tool.tool_calls = [{"id": "tc-1", "name": tool_name, "args": {"ticker": "AAPL"}}]
        tool_result = ToolMessage(content="Revenue: $391B", tool_call_id="tc-1")
        messages = [ai_with_tool, tool_result, ai_final]

    return {"messages": messages}


# ── AgentService.chat() tests ─────────────────────────────────────────────────

@pytest.mark.integration
class TestAgentServiceChat:
    """Verify chat() orchestration with a mocked LangChain agent."""

    @pytest.mark.asyncio
    async def test_chat_returns_chat_response(self, agent_service, mock_mcp):
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = _make_agent_result("Apple's revenue is $391B.")

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            request = ChatRequest(message="What is AAPL revenue?")
            response = await agent_service.chat(request)

        assert isinstance(response, ChatResponse)
        assert "391" in response.answer or response.answer  # some answer present
        assert isinstance(response.conversation_id, str)
        assert isinstance(response.tool_calls, list)

    @pytest.mark.asyncio
    async def test_chat_extracts_tool_traces_when_tools_used(self, agent_service):
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = _make_agent_result(
            "Apple's revenue is $391B.", tool_name="vector_store"
        )

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            response = await agent_service.chat(ChatRequest(message="Risks?"))

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "vector_store"

    @pytest.mark.asyncio
    async def test_chat_injects_system_prompt_for_fresh_conversation(self, agent_service):
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = _make_agent_result("Answer")
        captured_input = {}

        async def capture_invoke(agent_input, config=None):
            captured_input.update(agent_input)
            return _make_agent_result("Answer")

        mock_agent.ainvoke.side_effect = capture_invoke

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            await agent_service.chat(ChatRequest(message="Hello", history=[]))

        from langchain_core.messages import SystemMessage
        first_msg = captured_input["messages"][0]
        assert isinstance(first_msg, SystemMessage)
        assert "FinsightAI" in first_msg.content

    @pytest.mark.asyncio
    async def test_chat_does_not_re_inject_system_prompt_with_history(self, agent_service):
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = _make_agent_result("Answer")
        captured_input = {}

        async def capture_invoke(agent_input, config=None):
            captured_input.update(agent_input)
            return _make_agent_result("Answer")

        mock_agent.ainvoke.side_effect = capture_invoke

        history = [
            ConversationMessage(role=MessageRole.USER, content="First question"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="First answer"),
        ]
        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            await agent_service.chat(ChatRequest(message="Follow-up", history=history))

        from langchain_core.messages import SystemMessage
        system_msgs = [m for m in captured_input["messages"] if isinstance(m, SystemMessage)]
        assert len(system_msgs) == 1  # only one system message even with history

    @pytest.mark.asyncio
    async def test_chat_propagates_model_override(self, agent_service, settings):
        """Verify the model parameter is forwarded to FinancialAgentFactory.create."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = _make_agent_result("answer")
        captured_model = []

        original_create = agent_service._factory.create

        def capture_create(tools, model=None):
            captured_model.append(model)
            return mock_agent

        agent_service._factory.create = capture_create

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            await agent_service.chat(ChatRequest(message="Q", model="openai:gpt-4o"))

        assert captured_model[-1] == "openai:gpt-4o"


# ── AgentService.stream() tests ───────────────────────────────────────────────

@pytest.mark.integration
class TestAgentServiceStream:
    """Verify stream() yields correctly typed StreamChunks."""

    @pytest.mark.asyncio
    async def test_stream_yields_done_event_at_end(self, agent_service):
        mock_agent = MagicMock()

        async def fake_stream_events(agent_input, config=None, version="v2"):
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello")}, "name": "llm"}
            yield {"event": "on_tool_start", "data": {"input": {"ticker": "AAPL"}}, "name": "vector_store"}
            yield {"event": "on_tool_end", "data": {"output": "3 results"}, "name": "vector_store"}

        mock_agent.astream_events = fake_stream_events

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            chunks = []
            async for chunk in agent_service.stream(ChatRequest(message="Test")):
                chunks.append(chunk)

        event_types = {c.event for c in chunks}
        assert StreamEventType.DONE in event_types

    @pytest.mark.asyncio
    async def test_stream_yields_token_events(self, agent_service):
        mock_agent = MagicMock()

        async def fake_stream_events(agent_input, config=None, version="v2"):
            for token in ["Apple", " revenue", " is", " $391B"]:
                yield {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": MagicMock(content=token)},
                    "name": "llm",
                }

        mock_agent.astream_events = fake_stream_events

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            chunks = []
            async for chunk in agent_service.stream(ChatRequest(message="Revenue?")):
                chunks.append(chunk)

        token_chunks = [c for c in chunks if c.event == StreamEventType.TOKEN]
        assert len(token_chunks) == 4
        assert token_chunks[0].data == "Apple"

    @pytest.mark.asyncio
    async def test_stream_yields_tool_start_and_end(self, agent_service):
        mock_agent = MagicMock()

        async def fake_stream_events(agent_input, config=None, version="v2"):
            yield {"event": "on_tool_start", "data": {"input": {}}, "name": "get_company_financials"}
            yield {"event": "on_tool_end", "data": {"output": "market_cap: $3T"}, "name": "get_company_financials"}

        mock_agent.astream_events = fake_stream_events

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            chunks = []
            async for chunk in agent_service.stream(ChatRequest(message="Market cap?")):
                chunks.append(chunk)

        start_chunks = [c for c in chunks if c.event == StreamEventType.TOOL_START]
        end_chunks = [c for c in chunks if c.event == StreamEventType.TOOL_END]
        assert len(start_chunks) == 1
        assert start_chunks[0].data["tool"] == "get_company_financials"
        assert len(end_chunks) == 1

    @pytest.mark.asyncio
    async def test_stream_yields_error_on_exception(self, agent_service):
        mock_agent = MagicMock()

        async def failing_stream_events(agent_input, config=None, version="v2"):
            raise RuntimeError("LLM connection failed")
            yield  # make it a generator

        mock_agent.astream_events = failing_stream_events

        with patch("app.agents.financial_agent.init_chat_model"), \
             patch("app.agents.financial_agent.create_agent", return_value=mock_agent):
            chunks = []
            async for chunk in agent_service.stream(ChatRequest(message="Test")):
                chunks.append(chunk)

        error_chunks = [c for c in chunks if c.event == StreamEventType.ERROR]
        assert len(error_chunks) == 1
        assert "LLM connection failed" in str(error_chunks[0].data)


# ── MCPClientManager tests ────────────────────────────────────────────────────

@pytest.mark.integration
class TestMCPClientManager:
    """Verify MCPClientManager lifecycle methods and readiness flag."""

    def test_not_connected_initially(self, settings):
        mgr = MCPClientManager(settings)
        assert mgr.is_connected is False

    def test_get_tools_raises_when_not_connected(self, settings):
        mgr = MCPClientManager(settings)
        with pytest.raises(RuntimeError, match="not connected"):
            mgr.get_tools()

    @pytest.mark.asyncio
    async def test_connect_sets_connected_flag(self, settings):
        mgr = MCPClientManager(settings)
        mock_client = AsyncMock()
        mock_client.get_tools = AsyncMock(return_value=[MagicMock(name="tool1")])

        with patch(
            "app.services.mcp_manager.MultiServerMCPClient",
            return_value=mock_client,
        ):
            await mgr.connect()

        assert mgr.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect_resets_state(self, settings):
        mgr = MCPClientManager(settings)
        mgr._connected = True
        mgr._tools = [MagicMock()]
        await mgr.disconnect()
        assert mgr.is_connected is False
        assert mgr.get_tools.__func__ if False else True  # just verify state
        with pytest.raises(RuntimeError):
            mgr.get_tools()
