"""
Full-stack E2E tests using pytest + httpx.

These tests call the real running backend (configured via BACKEND_URL env var)
and assert end-to-end behaviour of the entire system:
  Backend API → AgentService → LangChain agent → MCP tools → Chroma / yfinance

Marked with @pytest.mark.e2e – excluded from normal CI.

Run with: pytest tests/e2e/ -m e2e -v --timeout=300

Prerequisites:
  - docker compose up (all services running)
  - BACKEND_URL=http://localhost:8001
  - OPENAI_API_KEY set in environment
"""

from __future__ import annotations

import os
import time
import uuid
import pytest
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
BASE = f"{BACKEND_URL}/api/v1"
TIMEOUT = 120  # seconds


@pytest.fixture(scope="module")
def http():
    """Module-scoped httpx client for the backend."""
    with httpx.Client(base_url=BACKEND_URL, timeout=TIMEOUT) as client:
        # Verify backend is reachable
        try:
            resp = client.get("/health")
            if resp.status_code != 200:
                pytest.skip(f"Backend not healthy: {resp.status_code}")
        except Exception as exc:
            pytest.skip(f"Backend not reachable at {BACKEND_URL}: {exc}")
        yield client


# ── Health checks ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestFullStackHealth:
    """Verify all services are healthy before running integration tests."""

    def test_backend_health(self, http):
        resp = http.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_agent_health(self, http):
        resp = http.get("/api/v1/agent/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "llm_model" in body

    def test_mcp_connected(self, http):
        resp = http.get("/api/v1/agent/health")
        assert resp.json()["mcp_connected"] is True, (
            "MCP server is not connected. Ensure the MCP service is running."
        )

    def test_models_list_non_empty(self, http):
        resp = http.get("/api/v1/agent/models")
        assert resp.status_code == 200
        assert len(resp.json()["models"]) >= 1


# ── Agent chat E2E ─────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestFullStackAgentChat:
    """End-to-end agent chat tests against the running backend."""

    def test_simple_factual_question(self, http):
        """Ask a simple question that doesn't require tools."""
        resp = http.post(
            "/api/v1/agent/chat",
            json={"message": "What does AAPL stand for?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["answer"]) > 20
        assert "Apple" in body["answer"] or "AAPL" in body["answer"]

    def test_financial_data_question_uses_tools(self, http):
        """Question requiring financial data should invoke at least one MCP tool."""
        resp = http.post(
            "/api/v1/agent/chat",
            json={"message": "What is Apple's current market cap?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["tool_calls"]) > 0, "Expected at least one MCP tool call"
        tool_names = [tc["tool_name"] for tc in body["tool_calls"]]
        assert "get_company_financials" in tool_names or "get_fundamentals" in tool_names

    def test_rag_question_uses_vector_store(self, http):
        """Question about 10-K risk factors should use vector_store tool."""
        resp = http.post(
            "/api/v1/agent/chat",
            json={"message": "What are the main risk factors in AAPL's 10-K filing?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        tool_names = [tc["tool_name"] for tc in body["tool_calls"]]
        assert "vector_store" in tool_names, (
            f"Expected vector_store tool for RAG question. Tools used: {tool_names}"
        )

    def test_conversation_id_echoed(self, http):
        """Conversation ID should be preserved across the response."""
        cid = str(uuid.uuid4())
        resp = http.post(
            "/api/v1/agent/chat",
            json={"message": "Hello", "conversation_id": cid},
        )
        assert resp.json()["conversation_id"] == cid

    def test_multi_turn_conversation(self, http):
        """Follow-up message in a conversation should receive a coherent response."""
        cid = str(uuid.uuid4())

        # First turn
        resp1 = http.post(
            "/api/v1/agent/chat",
            json={"message": "Tell me about AAPL", "conversation_id": cid},
        )
        assert resp1.status_code == 200
        first_answer = resp1.json()["answer"]

        # Second turn with history
        resp2 = http.post(
            "/api/v1/agent/chat",
            json={
                "message": "What are its main risks?",
                "conversation_id": cid,
                "history": [
                    {"role": "user", "content": "Tell me about AAPL"},
                    {"role": "assistant", "content": first_answer},
                ],
            },
        )
        assert resp2.status_code == 200
        second_answer = resp2.json()["answer"]
        assert len(second_answer) > 20

    def test_response_tokens_metadata(self, http):
        """Response should optionally include token count metadata."""
        resp = http.post(
            "/api/v1/agent/chat",
            json={"message": "What sector is MSFT in?"},
        )
        body = resp.json()
        # Token counts are optional (None is valid), but if present they must be positive
        if body.get("input_tokens") is not None:
            assert body["input_tokens"] > 0
        if body.get("output_tokens") is not None:
            assert body["output_tokens"] > 0


# ── Analysis E2E ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestFullStackAnalysis:
    """End-to-end analysis endpoint tests."""

    def test_outlook_returns_sentence(self, http):
        resp = http.get("/api/v1/analysis/outlook/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "AAPL"
        assert len(body["outlook"]) > 20

    def test_filing_risks_returns_list(self, http):
        resp = http.get("/api/v1/analysis/filing-risks/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["risks"], list)
        # Should return at least 1 risk for AAPL (10-K should be ingested)
        assert len(body["risks"]) >= 1

    def test_ai_themes_returns_string_list(self, http):
        resp = http.get("/api/v1/analysis/ai-themes/AAPL")
        assert resp.status_code == 200
        themes = resp.json()["themes"]
        assert isinstance(themes, list)
        for theme in themes:
            assert isinstance(theme, str)

    def test_market_news_returns_items(self, http):
        resp = http.get("/api/v1/analysis/market-news/AAPL")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert isinstance(items, list)


# ── Chat session CRUD E2E ─────────────────────────────────────────────────────

@pytest.mark.e2e
class TestFullStackChatCRUD:
    """End-to-end chat session CRUD with the real database."""

    def test_create_and_retrieve_session(self, http):
        uid = str(uuid.uuid4())

        # Create
        create_resp = http.post(
            "/api/v1/chats",
            json={"user_id": uid, "title": "E2E Test Chat"},
        )
        assert create_resp.status_code == 201
        session = create_resp.json()
        sid = session["id"]
        assert session["title"] == "E2E Test Chat"

        # Retrieve
        get_resp = http.get(f"/api/v1/chats/{sid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == sid

    def test_list_sessions_for_user(self, http):
        uid = str(uuid.uuid4())
        http.post("/api/v1/chats", json={"user_id": uid, "title": "Chat A"})
        http.post("/api/v1/chats", json={"user_id": uid, "title": "Chat B"})

        list_resp = http.get(f"/api/v1/chats?user_id={uid}")
        assert list_resp.status_code == 200
        sessions = list_resp.json()
        assert len(sessions) >= 2

    def test_update_session_title(self, http):
        uid = str(uuid.uuid4())
        create_resp = http.post("/api/v1/chats", json={"user_id": uid, "title": "Original"})
        sid = create_resp.json()["id"]

        update_resp = http.patch(f"/api/v1/chats/{sid}", json={"title": "Updated Title"})
        assert update_resp.status_code == 200

    def test_delete_session(self, http):
        uid = str(uuid.uuid4())
        create_resp = http.post("/api/v1/chats", json={"user_id": uid, "title": "To Delete"})
        sid = create_resp.json()["id"]

        delete_resp = http.delete(f"/api/v1/chats/{sid}")
        assert delete_resp.status_code == 204

        get_resp = http.get(f"/api/v1/chats/{sid}")
        assert get_resp.status_code == 404

    def test_get_nonexistent_session_returns_404(self, http):
        resp = http.get(f"/api/v1/chats/{uuid.uuid4()}")
        assert resp.status_code == 404
