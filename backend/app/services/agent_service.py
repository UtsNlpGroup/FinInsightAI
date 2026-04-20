"""
AgentService – Orchestrates all agent interactions.

Pattern: Service Layer
  The service sits between the HTTP layer (routes) and the domain layer
  (LangChain agent, MCP manager).  Routes never import LangChain or MCP
  directly; they only call AgentService methods, keeping concerns cleanly
  separated.

Pattern: Strategy (implicit)
  The agent is produced by an injected factory, so swapping the agent
  implementation requires no changes here.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agents.financial_agent import FinancialAgentFactory
from app.core.config import Settings
from app.schemas.agent import (
    ChatRequest,
    ChatResponse,
    ConversationMessage,
    MessageRole,
    StreamChunk,
    StreamEventType,
    ToolCallTrace,
)
from app.services.mcp_manager import MCPClientManager

logger = logging.getLogger(__name__)


# ── Message conversion helpers ────────────────────────────────────────────────

def _schema_messages_to_lc(history: list[ConversationMessage]) -> list:
    """Convert API ConversationMessage objects to LangChain message types."""
    lc_messages = []
    for msg in history:
        if msg.role == MessageRole.USER:
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role == MessageRole.TOOL:
            lc_messages.append(
                ToolMessage(
                    content=msg.content,
                    tool_call_id=msg.tool_call_id or "unknown",
                )
            )
    return lc_messages


def _extract_tool_traces(messages: list) -> list[ToolCallTrace]:
    """Walk the final message list and extract ordered tool-call traces."""
    traces: list[ToolCallTrace] = []
    pending: dict[str, dict[str, Any]] = {}

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                pending[tc["id"]] = {"name": tc["name"], "input": tc["args"]}

        elif isinstance(msg, ToolMessage):
            meta = pending.pop(msg.tool_call_id, {})
            traces.append(
                ToolCallTrace(
                    tool_name=meta.get("name", "unknown"),
                    input=meta.get("input", {}),
                    output=msg.content,
                )
            )
    return traces


# ── Service ───────────────────────────────────────────────────────────────────

class AgentService:
    """
    Provides `chat()` and `stream()` operations on top of the LangChain agent.

    Both methods are async and safe to call concurrently.  A fresh agent
    invocation is created per request; the MCP session is managed by
    MCPClientManager at the application level.
    """

    def __init__(self, mcp_manager: MCPClientManager, settings: Settings) -> None:
        self._mcp_manager = mcp_manager
        self._settings = settings
        self._factory = FinancialAgentFactory(settings)

    # ── Internal builders ─────────────────────────────────────────────────────

    def _build_agent(self, model: str | None = None) -> Any:
        """
        Retrieve MCP tools and produce a ready-to-invoke LangChain agent.

        Args:
            model: Optional LangChain model ID override (e.g. "openai:gpt-4.1").
                   Falls back to the server default when ``None``.
        """
        tools = self._mcp_manager.get_tools()
        logger.info(
            "Agent built | available_tools=[%s]",
            ", ".join(t.name for t in tools),
        )
        return self._factory.create(tools, model=model)

    def _build_input(self, request: ChatRequest) -> dict:
        """
        Construct the agent input dict from the API request.

        The system prompt is prepended as the first message on the first
        turn of any conversation so the agent always has its persona and
        guidelines in context.
        """
        messages: list = []

        # Inject system prompt when starting a fresh conversation
        history_has_system = any(
            isinstance(m, SystemMessage)
            for m in _schema_messages_to_lc(request.history)
        )
        if not request.history or not history_has_system:
            messages.append(SystemMessage(content=self._factory.system_prompt))

        messages.extend(_schema_messages_to_lc(request.history))
        messages.append(HumanMessage(content=request.message))

        return {"messages": messages}

    # ── Blocking chat ─────────────────────────────────────────────────────────

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Run the LangChain agent to completion and return the full response.

        The agent uses `create_agent` under the hood and communicates with
        the MCP server to invoke `get_company_financials` and `vector_store`
        tools as needed.

        Raises:
            RuntimeError: If the MCP client is not connected.
            Exception: Any error raised by the LLM or MCP tools is propagated.
        """
        agent = self._build_agent(model=request.model)
        agent_input = self._build_input(request)

        config = {"recursion_limit": self._settings.agent_recursion_limit}
        result = await agent.ainvoke(agent_input, config=config)

        final_messages = result["messages"]

        for msg in final_messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    logger.info(
                        "Tool call dispatched | tool=%s | input=%s",
                        tc["name"],
                        tc["args"],
                    )
            elif isinstance(msg, ToolMessage):
                logger.info(
                    "Tool call result    | tool_call_id=%s | output=%.200s",
                    msg.tool_call_id,
                    msg.content,
                )

        answer_msg: AIMessage | None = next(
            (m for m in reversed(final_messages) if isinstance(m, AIMessage)),
            None,
        )
        answer = answer_msg.content if answer_msg else ""
        usage = getattr(answer_msg, "usage_metadata", None) if answer_msg else None

        return ChatResponse(
            conversation_id=request.conversation_id,
            answer=answer,
            tool_calls=_extract_tool_traces(final_messages),
            input_tokens=usage.get("input_tokens") if usage else None,
            output_tokens=usage.get("output_tokens") if usage else None,
        )

    # ── Streaming chat ────────────────────────────────────────────────────────

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """
        Stream agent events via `astream_events` as they happen.

        Yields StreamChunk objects for:
          - Each LLM text token   (event=TOKEN)
          - Tool invocation start  (event=TOOL_START)
          - Tool invocation end    (event=TOOL_END)
          - Final completion       (event=DONE)
          - Any error              (event=ERROR)
        """
        agent = self._build_agent(model=request.model)
        agent_input = self._build_input(request)
        config = {"recursion_limit": self._settings.agent_recursion_limit}
        cid = request.conversation_id

        try:
            async for event in agent.astream_events(
                agent_input, config=config, version="v2"
            ):
                kind = event.get("event", "")
                name = event.get("name", "")

                # LLM streaming tokens
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    token = getattr(chunk, "content", "") if chunk else ""
                    if token:
                        yield StreamChunk(
                            event=StreamEventType.TOKEN,
                            data=token,
                            conversation_id=cid,
                        )

                # MCP tool invocation start
                elif kind == "on_tool_start":
                    tool_input = event["data"].get("input", {})
                    logger.info(
                        "Tool call dispatched | tool=%s | input=%s",
                        name,
                        tool_input,
                    )
                    yield StreamChunk(
                        event=StreamEventType.TOOL_START,
                        data={"tool": name, "input": tool_input},
                        conversation_id=cid,
                    )

                # MCP tool invocation end
                elif kind == "on_tool_end":
                    tool_output = str(event["data"].get("output", ""))
                    logger.info(
                        "Tool call result    | tool=%s | output=%.200s",
                        name,
                        tool_output,
                    )
                    yield StreamChunk(
                        event=StreamEventType.TOOL_END,
                        data={"tool": name, "output": tool_output},
                        conversation_id=cid,
                    )

            yield StreamChunk(
                event=StreamEventType.DONE,
                data={"conversation_id": cid},
                conversation_id=cid,
            )

        except Exception as exc:
            logger.exception("Error during agent stream | conversation_id=%s", cid)
            yield StreamChunk(
                event=StreamEventType.ERROR,
                data={"error": str(exc)},
                conversation_id=cid,
            )
