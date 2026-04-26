"""
API contract tests for /api/v1/chats/* endpoints.

Tests full CRUD lifecycle: create → list → get → update → delete.
Uses the mock ChatService from the root conftest.
"""

from __future__ import annotations

import uuid
import pytest


# ── POST /api/v1/chats ────────────────────────────────────────────────────────

@pytest.mark.api
class TestCreateSession:

    def test_returns_201_on_creation(self, client):
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": str(uuid.uuid4()), "title": "My first chat"},
        )
        assert resp.status_code == 201

    def test_response_has_session_id(self, client):
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": str(uuid.uuid4()), "title": "Test"},
        )
        body = resp.json()
        assert "id" in body
        assert body["id"]  # not None/empty

    def test_response_has_user_id(self, client):
        uid = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": uid, "title": "Test"},
        )
        assert "user_id" in resp.json()

    def test_response_has_title(self, client):
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": str(uuid.uuid4()), "title": "AAPL Analysis"},
        )
        assert "title" in resp.json()

    def test_response_has_messages_list(self, client):
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": str(uuid.uuid4()), "title": "Chat"},
        )
        assert isinstance(resp.json().get("messages"), list)

    def test_response_has_timestamps(self, client):
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": str(uuid.uuid4()), "title": "Chat"},
        )
        body = resp.json()
        assert "created_at" in body
        assert "updated_at" in body

    def test_returns_422_for_missing_user_id(self, client):
        resp = client.post("/api/v1/chats", json={"title": "No user"})
        assert resp.status_code == 422

    def test_returns_422_for_invalid_user_id_format(self, client):
        resp = client.post(
            "/api/v1/chats",
            json={"user_id": "not-a-uuid", "title": "Test"},
        )
        assert resp.status_code == 422


# ── GET /api/v1/chats ─────────────────────────────────────────────────────────

@pytest.mark.api
class TestListSessions:

    def test_returns_200_with_valid_user_id(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}")
        assert resp.status_code == 200

    def test_returns_list(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}")
        assert isinstance(resp.json(), list)

    def test_each_summary_has_id_and_title(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}")
        for session in resp.json():
            assert "id" in session
            assert "title" in session

    def test_returns_422_for_missing_user_id(self, client):
        resp = client.get("/api/v1/chats")
        assert resp.status_code == 422

    def test_limit_parameter_accepted(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}&limit=10")
        assert resp.status_code == 200

    def test_offset_parameter_accepted(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}&offset=5")
        assert resp.status_code == 200

    def test_limit_too_large_returns_422(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}&limit=201")
        assert resp.status_code == 422

    def test_negative_limit_returns_422(self, client):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats?user_id={uid}&limit=0")
        assert resp.status_code == 422


# ── GET /api/v1/chats/{session_id} ────────────────────────────────────────────

@pytest.mark.api
class TestGetSession:

    def test_returns_200_for_existing_session(self, client):
        sid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats/{sid}")
        assert resp.status_code == 200

    def test_response_has_full_session_data(self, client):
        sid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats/{sid}")
        body = resp.json()
        assert "id" in body
        assert "messages" in body
        assert "title" in body

    def test_returns_404_for_nonexistent_session(self, client, mock_chat_service):
        mock_chat_service.get_session.return_value = None
        sid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/chats/{sid}")
        assert resp.status_code == 404

    def test_returns_422_for_invalid_uuid_format(self, client):
        resp = client.get("/api/v1/chats/not-a-real-uuid")
        assert resp.status_code == 422


# ── PATCH /api/v1/chats/{session_id} ─────────────────────────────────────────

@pytest.mark.api
class TestUpdateSession:

    def test_returns_200_for_title_update(self, client):
        sid = str(uuid.uuid4())
        resp = client.patch(
            f"/api/v1/chats/{sid}",
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200

    def test_response_contains_updated_session(self, client):
        sid = str(uuid.uuid4())
        resp = client.patch(
            f"/api/v1/chats/{sid}",
            json={"title": "New Title"},
        )
        body = resp.json()
        assert "id" in body
        assert "title" in body

    def test_returns_404_when_session_not_found(self, client, mock_chat_service):
        mock_chat_service.update_session.return_value = None
        sid = str(uuid.uuid4())
        resp = client.patch(f"/api/v1/chats/{sid}", json={"title": "x"})
        assert resp.status_code == 404


# ── DELETE /api/v1/chats/{session_id} ────────────────────────────────────────

@pytest.mark.api
class TestDeleteSession:

    def test_returns_204_on_success(self, client):
        sid = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/chats/{sid}")
        assert resp.status_code == 204

    def test_returns_404_when_session_not_found(self, client, mock_chat_service):
        mock_chat_service.delete_session.return_value = False
        sid = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/chats/{sid}")
        assert resp.status_code == 404

    def test_204_has_no_body(self, client):
        sid = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/chats/{sid}")
        assert resp.status_code == 204
        assert not resp.content
