"""
Pydantic schemas for the Chat Sessions API (normalised schema).

Tables
------
chat_sessions  – session metadata (id, user_id, title, timestamps)
chat_messages  – individual message rows linked to a session
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent import MessageRole


# ── Individual message ────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    """A single message to insert into chat_messages."""

    role: MessageRole
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    suggestions: list[str] | None = None
    cards: list[dict[str, Any]] | None = None
    citations: str | None = None
    is_greeting: bool = False


class ChatMessageResponse(BaseModel):
    """A message row returned from chat_messages."""

    id: int
    session_id: UUID
    role: MessageRole
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    suggestions: list[str] | None = None
    cards: list[dict[str, Any]] | None = None
    citations: str | None = None
    is_greeting: bool
    created_at: datetime


# ── Session request bodies ────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    """Body accepted by POST /chats."""

    user_id: UUID = Field(description="Supabase auth UID of the session owner.")
    title: str = Field(
        default="New Chat",
        max_length=200,
        description="Human-readable label shown in the sidebar.",
    )


class ChatSessionUpdate(BaseModel):
    """Body accepted by PATCH /chats/{id}. All fields are optional."""

    title: str | None = Field(default=None, max_length=200)
    messages: list[ChatMessageCreate] | None = Field(
        default=None,
        description=(
            "Full replacement of the session's message list. "
            "Replaces all existing rows in chat_messages for this session."
        ),
    )


# ── Session response bodies ───────────────────────────────────────────────────

class ChatSessionResponse(BaseModel):
    """Returned by every read/write chat-session endpoint."""

    id: UUID
    user_id: UUID
    title: str
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatSessionSummary(BaseModel):
    """Lightweight projection used in list responses (omits messages)."""

    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
