"""
Pydantic schemas for the Agent API.

Separating schemas from models keeps the HTTP contract explicit and independent
of internal domain objects.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Conversation primitives ───────────────────────────────────────────────────

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    """A single turn in a conversation thread."""

    role: MessageRole
    content: str
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Raw tool-call payloads attached to this message (assistant turns only).",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="ID linking a tool result back to its originating tool call.",
    )


# ── Request ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Body accepted by POST /agent/chat and POST /agent/stream."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=8_000,
        description="The user's latest message.",
        examples=["What are the key financials for Apple?"],
    )
    conversation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Client-supplied ID to group turns into a thread. Auto-generated if omitted.",
    )
    history: list[ConversationMessage] = Field(
        default_factory=list,
        description=(
            "Previous turns to include as context. "
            "Ordered oldest → newest. Maximum 50 messages."
        ),
        max_length=50,
    )
    stream: bool = Field(
        default=False,
        description="When true, use the /stream endpoint instead of /chat for SSE delivery.",
    )


# ── Tool-use trace ────────────────────────────────────────────────────────────

class ToolCallTrace(BaseModel):
    """Describes a single MCP tool invocation made by the agent."""

    tool_name: str
    input: dict[str, Any]
    output: Any
    error: str | None = None


# ── Response ──────────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Body returned by POST /agent/chat."""

    conversation_id: str
    answer: str = Field(description="Final natural-language answer from the agent.")
    tool_calls: list[ToolCallTrace] = Field(
        default_factory=list,
        description="Ordered list of MCP tools the agent invoked to produce the answer.",
    )
    input_tokens: int | None = None
    output_tokens: int | None = None


# ── Streaming chunk ───────────────────────────────────────────────────────────

class StreamEventType(str, Enum):
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    DONE = "done"
    ERROR = "error"


class StreamChunk(BaseModel):
    """One SSE data payload during a streaming agent response."""

    event: StreamEventType
    data: str | dict[str, Any]
    conversation_id: str


# ── Health / meta ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    mcp_connected: bool
    llm_model: str
    version: str
