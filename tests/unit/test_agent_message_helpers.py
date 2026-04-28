"""
Unit tests for backend/app/services/agent_service.py helper functions.

Tests the pure conversion functions _schema_messages_to_lc and _extract_tool_traces
without touching the LLM or MCP.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.schemas.agent import ConversationMessage, MessageRole, ToolCallTrace
from app.services.agent_service import _extract_tool_traces, _schema_messages_to_lc


# ── _schema_messages_to_lc ────────────────────────────────────────────────────

class TestSchemaMessagesToLC:
    """Verify ConversationMessage → LangChain message conversion."""

    def test_user_message_becomes_human_message(self):
        msgs = [ConversationMessage(role=MessageRole.USER, content="Hello")]
        result = _schema_messages_to_lc(msgs)
        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello"

    def test_assistant_message_becomes_ai_message(self):
        msgs = [ConversationMessage(role=MessageRole.ASSISTANT, content="Hi there!")]
        result = _schema_messages_to_lc(msgs)
        assert isinstance(result[0], AIMessage)

    def test_tool_message_becomes_tool_message(self):
        msgs = [
            ConversationMessage(
                role=MessageRole.TOOL,
                content="Result data",
                tool_call_id="tc-001",
            )
        ]
        result = _schema_messages_to_lc(msgs)
        assert isinstance(result[0], ToolMessage)
        assert result[0].tool_call_id == "tc-001"

    def test_tool_message_without_id_uses_unknown(self):
        msgs = [ConversationMessage(role=MessageRole.TOOL, content="data")]
        result = _schema_messages_to_lc(msgs)
        assert isinstance(result[0], ToolMessage)
        assert result[0].tool_call_id == "unknown"

    def test_empty_history_returns_empty_list(self):
        assert _schema_messages_to_lc([]) == []

    def test_ordering_preserved(self):
        msgs = [
            ConversationMessage(role=MessageRole.USER, content="q1"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="a1"),
            ConversationMessage(role=MessageRole.USER, content="q2"),
        ]
        result = _schema_messages_to_lc(msgs)
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)
        assert isinstance(result[2], HumanMessage)

    def test_system_role_is_not_converted(self):
        """System messages in history should be silently skipped (not converted)."""
        msgs = [ConversationMessage(role=MessageRole.SYSTEM, content="system note")]
        result = _schema_messages_to_lc(msgs)
        assert len(result) == 0

    def test_mixed_conversation_converts_all_roles(self):
        msgs = [
            ConversationMessage(role=MessageRole.USER, content="Analyse AAPL"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="Looking up data…"),
            ConversationMessage(role=MessageRole.TOOL, content="Revenue: $391B", tool_call_id="tc-1"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="Apple's revenue is $391B."),
        ]
        result = _schema_messages_to_lc(msgs)
        assert len(result) == 4
        assert isinstance(result[2], ToolMessage)


# ── _extract_tool_traces ──────────────────────────────────────────────────────

class TestExtractToolTraces:
    """Verify tool call trace extraction from a final message list."""

    def _make_ai_with_tool_call(self, tool_id: str, name: str, args: dict) -> AIMessage:
        msg = AIMessage(content="")
        msg.tool_calls = [{"id": tool_id, "name": name, "args": args}]
        return msg

    def test_single_tool_call_produces_one_trace(self):
        ai_msg = self._make_ai_with_tool_call("tc-1", "vector_store", {"query": "risks"})
        tool_msg = ToolMessage(content="3 results", tool_call_id="tc-1")
        traces = _extract_tool_traces([ai_msg, tool_msg])
        assert len(traces) == 1
        assert traces[0].tool_name == "vector_store"
        assert traces[0].input == {"query": "risks"}
        assert traces[0].output == "3 results"

    def test_multiple_sequential_tool_calls(self):
        ai1 = self._make_ai_with_tool_call("tc-1", "get_company_financials", {"ticker": "AAPL"})
        tool1 = ToolMessage(content="market cap: $3T", tool_call_id="tc-1")
        ai2 = self._make_ai_with_tool_call("tc-2", "vector_store", {"query_text": "risks"})
        tool2 = ToolMessage(content="risk factors...", tool_call_id="tc-2")

        traces = _extract_tool_traces([ai1, tool1, ai2, tool2])
        assert len(traces) == 2
        assert traces[0].tool_name == "get_company_financials"
        assert traces[1].tool_name == "vector_store"

    def test_no_tool_calls_returns_empty_list(self):
        ai_msg = AIMessage(content="Here is the answer.")
        ai_msg.tool_calls = []
        traces = _extract_tool_traces([ai_msg])
        assert traces == []

    def test_empty_messages_returns_empty_list(self):
        assert _extract_tool_traces([]) == []

    def test_tool_result_without_matching_ai_uses_unknown(self):
        """ToolMessage with no matching pending AIMessage should use 'unknown' tool name."""
        orphan_tool = ToolMessage(content="some data", tool_call_id="tc-orphan")
        traces = _extract_tool_traces([orphan_tool])
        assert len(traces) == 1
        assert traces[0].tool_name == "unknown"

    def test_trace_preserves_full_input_dict(self):
        ai_msg = self._make_ai_with_tool_call(
            "tc-1",
            "vector_store",
            {"collection_name": "sec_filings", "query_text": "revenue", "n_results": 5},
        )
        tool_msg = ToolMessage(content="results", tool_call_id="tc-1")
        traces = _extract_tool_traces([ai_msg, tool_msg])
        assert traces[0].input["collection_name"] == "sec_filings"
        assert traces[0].input["n_results"] == 5
