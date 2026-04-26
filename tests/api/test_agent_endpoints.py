"""
API contract tests for /api/v1/agent/* endpoints.

Uses FastAPI TestClient with all external dependencies mocked (see root conftest).
Tests HTTP status codes, response schemas, validation errors, and SSE streaming.
"""

from __future__ import annotations

import json
import pytest

from app.schemas.agent import StreamEventType


# ── POST /api/v1/agent/chat ───────────────────────────────────────────────────

@pytest.mark.api
class TestAgentChat:
    """Contract tests for the blocking chat endpoint."""

    def test_returns_200_with_valid_payload(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "What is AAPL revenue?"},
        )
        assert resp.status_code == 200

    def test_response_has_answer_field(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "What is AAPL revenue?"},
        )
        body = resp.json()
        assert "answer" in body
        assert isinstance(body["answer"], str)
        assert len(body["answer"]) > 0

    def test_response_has_conversation_id(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Hello"},
        )
        body = resp.json()
        assert "conversation_id" in body

    def test_response_has_tool_calls_list(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Analyse AAPL"},
        )
        body = resp.json()
        assert "tool_calls" in body
        assert isinstance(body["tool_calls"], list)

    def test_tool_call_trace_has_required_fields(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Analyse AAPL"},
        )
        tool_calls = resp.json()["tool_calls"]
        if tool_calls:
            tc = tool_calls[0]
            assert "tool_name" in tc
            assert "input" in tc
            assert "output" in tc

    def test_custom_conversation_id_is_echoed(self, client):
        cid = "my-custom-conversation-id-abc123"
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Hello", "conversation_id": cid},
        )
        assert resp.json()["conversation_id"] == cid

    def test_model_override_accepted(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Hello", "model": "openai:gpt-4o"},
        )
        assert resp.status_code == 200

    def test_empty_history_accepted(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Hello", "history": []},
        )
        assert resp.status_code == 200

    def test_history_with_messages_accepted(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={
                "message": "Follow-up question",
                "history": [
                    {"role": "user", "content": "First question"},
                    {"role": "assistant", "content": "First answer"},
                ],
            },
        )
        assert resp.status_code == 200

    def test_returns_422_for_missing_message(self, client):
        resp = client.post("/api/v1/agent/chat", json={"model": "openai:gpt-4o"})
        assert resp.status_code == 422

    def test_returns_422_for_empty_message(self, client):
        resp = client.post("/api/v1/agent/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_returns_422_for_message_exceeding_max_length(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "x" * 8_001},  # max is 8_000
        )
        assert resp.status_code == 422

    def test_returns_422_for_history_exceeding_50_messages(self, client):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(51)]
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "Last message", "history": history},
        )
        assert resp.status_code == 422

    def test_content_type_is_json(self, client):
        resp = client.post(
            "/api/v1/agent/chat",
            json={"message": "test"},
        )
        assert "application/json" in resp.headers["content-type"]


# ── POST /api/v1/agent/stream ─────────────────────────────────────────────────

@pytest.mark.api
class TestAgentStream:
    """Contract tests for the Server-Sent Events streaming endpoint."""

    def test_returns_200_with_event_stream_content_type(self, client):
        with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "Stream test"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_stream_emits_done_event(self, client):
        with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "Stream test"},
        ) as resp:
            lines = list(resp.iter_lines())

        data_lines = [l for l in lines if l.startswith("data:")]
        events = []
        for line in data_lines:
            payload = json.loads(line[len("data:"):].strip())
            events.append(payload.get("event"))

        assert StreamEventType.DONE in events

    def test_stream_emits_token_events(self, client):
        with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "Token test"},
        ) as resp:
            lines = list(resp.iter_lines())

        token_events = []
        for line in lines:
            if line.startswith("data:"):
                payload = json.loads(line[len("data:"):].strip())
                if payload.get("event") == StreamEventType.TOKEN:
                    token_events.append(payload)

        assert len(token_events) > 0
        assert all("data" in e for e in token_events)

    def test_stream_emits_tool_start_and_end(self, client):
        with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "Tool test"},
        ) as resp:
            lines = list(resp.iter_lines())

        events = {}
        for line in lines:
            if line.startswith("data:"):
                payload = json.loads(line[len("data:"):].strip())
                evt = payload.get("event")
                events[evt] = events.get(evt, 0) + 1

        assert StreamEventType.TOOL_START in events
        assert StreamEventType.TOOL_END in events

    def test_each_sse_chunk_is_valid_json(self, client):
        with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "JSON check"},
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    payload_str = line[len("data:"):].strip()
                    parsed = json.loads(payload_str)
                    assert "event" in parsed
                    assert "conversation_id" in parsed

    def test_returns_422_for_missing_message(self, client):
        resp = client.post("/api/v1/agent/stream", json={})
        assert resp.status_code == 422


# ── GET /api/v1/agent/models ──────────────────────────────────────────────────

@pytest.mark.api
class TestAgentModels:
    """Contract tests for the models list endpoint."""

    def test_returns_200(self, client):
        resp = client.get("/api/v1/agent/models")
        assert resp.status_code == 200

    def test_response_has_models_list(self, client):
        resp = client.get("/api/v1/agent/models")
        body = resp.json()
        assert "models" in body
        assert isinstance(body["models"], list)
        assert len(body["models"]) >= 1

    def test_response_has_default_model(self, client):
        resp = client.get("/api/v1/agent/models")
        body = resp.json()
        assert "default_model" in body
        assert isinstance(body["default_model"], str)

    def test_each_model_has_id_and_label(self, client):
        resp = client.get("/api/v1/agent/models")
        for model in resp.json()["models"]:
            assert "id" in model
            assert "label" in model

    def test_exactly_one_model_is_marked_default(self, client):
        resp = client.get("/api/v1/agent/models")
        defaults = [m for m in resp.json()["models"] if m.get("is_default")]
        assert len(defaults) == 1


# ── GET /api/v1/agent/health ──────────────────────────────────────────────────

@pytest.mark.api
class TestAgentHealth:
    """Contract tests for the agent health endpoint."""

    def test_returns_200(self, client):
        resp = client.get("/api/v1/agent/health")
        assert resp.status_code == 200

    def test_response_has_status_ok(self, client):
        resp = client.get("/api/v1/agent/health")
        body = resp.json()
        assert body.get("status") == "ok"

    def test_response_has_mcp_connected_flag(self, client):
        resp = client.get("/api/v1/agent/health")
        body = resp.json()
        assert "mcp_connected" in body
        assert isinstance(body["mcp_connected"], bool)

    def test_response_has_llm_model(self, client):
        resp = client.get("/api/v1/agent/health")
        body = resp.json()
        assert "llm_model" in body


# ── GET /health (root) ────────────────────────────────────────────────────────

@pytest.mark.api
class TestRootHealth:
    def test_root_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.json()["status"] == "ok"

    def test_root_health_returns_version(self, client):
        resp = client.get("/health")
        assert "version" in resp.json()
