"""
Chat session endpoints – v1.

Exposes five routes under /api/v1/chats:
  POST   /             – Create a new chat session.
  GET    /             – List sessions for a user (query param: user_id).
  GET    /{id}         – Fetch a single session with its full message history.
  PATCH  /{id}         – Update title and/or messages of a session.
  DELETE /{id}         – Permanently delete a session.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_chat_service
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionSummary,
    ChatSessionUpdate,
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["Chat Sessions"])


# ── POST / ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    body: ChatSessionCreate,
    svc: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    try:
        return await svc.create_session(body)
    except Exception as exc:
        logger.exception("Failed to create chat session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


# ── GET / ─────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[ChatSessionSummary],
    summary="List chat sessions for a user",
)
async def list_sessions(
    user_id: UUID = Query(..., description="Filter sessions by this user ID."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    svc: ChatService = Depends(get_chat_service),
) -> list[ChatSessionSummary]:
    try:
        return await svc.list_sessions(user_id=user_id, limit=limit, offset=offset)
    except Exception as exc:
        logger.exception("Failed to list chat sessions for user=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


# ── GET /{id} ─────────────────────────────────────────────────────────────────

@router.get(
    "/{session_id}",
    response_model=ChatSessionResponse,
    summary="Get a single chat session",
)
async def get_session(
    session_id: UUID,
    svc: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found.",
        )
    return session


# ── PATCH /{id} ───────────────────────────────────────────────────────────────

@router.patch(
    "/{session_id}",
    response_model=ChatSessionResponse,
    summary="Update a chat session (title and/or messages)",
)
async def update_session(
    session_id: UUID,
    body: ChatSessionUpdate,
    svc: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    session = await svc.update_session(session_id, body)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found.",
        )
    return session


# ── DELETE /{id} ──────────────────────────────────────────────────────────────

@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: UUID,
    svc: ChatService = Depends(get_chat_service),
) -> None:
    deleted = await svc.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found.",
        )
