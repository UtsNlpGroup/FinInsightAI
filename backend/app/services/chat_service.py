"""
ChatService – CRUD for the normalised chat schema.

Tables
------
chat_sessions  – session metadata only (id, user_id, title, timestamps)
chat_messages  – individual message rows (foreign key → chat_sessions.id)

The messages table uses ON DELETE CASCADE, so deleting a session automatically
removes all of its messages.

Schema reference (run once in Supabase SQL Editor)
---------------------------------------------------
alter table public.chat_sessions
  drop column if exists messages,
  drop column if exists api_history;

create table if not exists public.chat_messages (
    id           bigint      generated always as identity primary key,
    session_id   uuid        not null references public.chat_sessions(id) on delete cascade,
    role         text        not null check (role in ('user','assistant','tool','system')),
    content      text        not null default '',
    tool_calls   jsonb,
    tool_call_id text,
    suggestions  jsonb,
    cards        jsonb,
    citations    text,
    is_greeting  boolean     not null default false,
    created_at   timestamptz not null default now()
);

create index if not exists chat_messages_session_idx
    on public.chat_messages (session_id, id asc);
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from uuid import UUID

from app.core.database import get_pool
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionSummary,
    ChatSessionUpdate,
)

if TYPE_CHECKING:
    from asyncpg import Connection, Record

logger = logging.getLogger(__name__)


# ── Row → schema helpers ──────────────────────────────────────────────────────

def _row_to_message(row: "Record") -> ChatMessageResponse:
    def _json(val: object) -> object:
        if isinstance(val, str):
            return json.loads(val)
        return val

    return ChatMessageResponse(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        tool_calls=_json(row["tool_calls"]) if row["tool_calls"] else None,
        tool_call_id=row["tool_call_id"],
        suggestions=_json(row["suggestions"]) if row["suggestions"] else None,
        cards=_json(row["cards"]) if row["cards"] else None,
        citations=row["citations"],
        is_greeting=row["is_greeting"],
        created_at=row["created_at"],
    )


def _record_to_session(
    session_row: "Record",
    message_rows: list["Record"],
) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session_row["id"],
        user_id=session_row["user_id"],
        title=session_row["title"],
        messages=[_row_to_message(r) for r in message_rows],
        created_at=session_row["created_at"],
        updated_at=session_row["updated_at"],
    )


def _record_to_summary(row: "Record") -> ChatSessionSummary:
    return ChatSessionSummary(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ── Internal message sync helper ──────────────────────────────────────────────

async def _sync_messages(
    conn: "Connection",
    session_id: UUID,
    messages: list[ChatMessageCreate],
) -> None:
    """Delete all existing messages for *session_id* and insert *messages*."""
    await conn.execute(
        "delete from public.chat_messages where session_id = $1",
        session_id,
    )
    if not messages:
        return

    await conn.executemany(
        """
        insert into public.chat_messages
            (session_id, role, content, tool_calls, tool_call_id,
             suggestions, cards, citations, is_greeting)
        values ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7::jsonb, $8, $9)
        """,
        [
            (
                session_id,
                m.role.value,
                m.content,
                json.dumps(m.tool_calls) if m.tool_calls is not None else None,
                m.tool_call_id,
                json.dumps(m.suggestions) if m.suggestions is not None else None,
                json.dumps(m.cards) if m.cards is not None else None,
                m.citations,
                m.is_greeting,
            )
            for m in messages
        ],
    )
    logger.info("Synced %d messages for session %s", len(messages), session_id)


# ── Service ───────────────────────────────────────────────────────────────────

class ChatService:
    """
    Async CRUD service for the normalised chat schema.

    All methods acquire a connection from the shared asyncpg pool and release
    it automatically via the async context manager.
    """

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_session(self, body: ChatSessionCreate) -> ChatSessionResponse:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                insert into public.chat_sessions (user_id, title)
                values ($1, $2)
                returning *
                """,
                body.user_id,
                body.title,
            )
        logger.info("Created chat session id=%s for user=%s", row["id"], row["user_id"])
        return _record_to_session(row, [])

    # ── List (metadata only) ──────────────────────────────────────────────────

    async def list_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSessionSummary]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select id, user_id, title, created_at, updated_at
                from   public.chat_sessions
                where  user_id = $1
                order  by updated_at desc
                limit  $2 offset $3
                """,
                user_id,
                limit,
                offset,
            )
        return [_record_to_summary(r) for r in rows]

    # ── Get (session + messages) ──────────────────────────────────────────────

    async def get_session(self, session_id: UUID) -> ChatSessionResponse | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            session_row = await conn.fetchrow(
                "select * from public.chat_sessions where id = $1",
                session_id,
            )
            if not session_row:
                return None
            msg_rows = await conn.fetch(
                """
                select * from public.chat_messages
                where  session_id = $1
                order  by id asc
                """,
                session_id,
            )
        return _record_to_session(session_row, list(msg_rows))

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_session(
        self,
        session_id: UUID,
        body: ChatSessionUpdate,
    ) -> ChatSessionResponse | None:
        if body.title is None and body.messages is None:
            return await self.get_session(session_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            # Update session metadata if title changed
            if body.title is not None:
                session_row = await conn.fetchrow(
                    """
                    update public.chat_sessions
                    set    title = $1, updated_at = now()
                    where  id = $2
                    returning *
                    """,
                    body.title,
                    session_id,
                )
            else:
                session_row = await conn.fetchrow(
                    """
                    update public.chat_sessions
                    set    updated_at = now()
                    where  id = $1
                    returning *
                    """,
                    session_id,
                )

            if not session_row:
                return None

            # Sync messages if provided
            if body.messages is not None:
                await _sync_messages(conn, session_id, body.messages)

            msg_rows = await conn.fetch(
                "select * from public.chat_messages where session_id = $1 order by id asc",
                session_id,
            )

        logger.info("Updated chat session id=%s", session_id)
        return _record_to_session(session_row, list(msg_rows))

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_session(self, session_id: UUID) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "delete from public.chat_sessions where id = $1",
                session_id,
            )
        deleted = result == "DELETE 1"
        if deleted:
            logger.info("Deleted chat session id=%s (messages cascade-deleted)", session_id)
        return deleted
