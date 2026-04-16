"""
Agent endpoints – v1.

Exposes three routes under /api/v1/agent:
  POST /chat    – Blocking: run agent to completion, return full answer.
  POST /stream  – Streaming: return SSE stream of agent events.
  GET  /health  – Readiness check: MCP connectivity + LLM config.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.dependencies import get_agent_service, get_mcp_manager
from app.schemas.agent import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    StreamChunk,
)
from app.services.agent_service import AgentService
from app.services.mcp_manager import MCPClientManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


# ── POST /chat ────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the financial agent",
    description=(
        "Runs the LangGraph ReAct agent to completion. "
        "Accepts an optional conversation history so multi-turn dialogues "
        "are fully supported. Returns the final answer and a trace of every "
        "MCP tool call the agent made."
    ),
    status_code=status.HTTP_200_OK,
)
async def chat(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> ChatResponse:
    logger.info(
        "Chat request | conversation_id=%s | message_length=%d",
        request.conversation_id,
        len(request.message),
    )
    try:
        return await agent_service.chat(request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /chat for conversation %s", request.conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        ) from exc


# ── POST /stream ──────────────────────────────────────────────────────────────

@router.post(
    "/stream",
    summary="Stream agent events via Server-Sent Events",
    description=(
        "Returns a text/event-stream response. Each SSE `data:` line is a JSON "
        "object matching the StreamChunk schema. Event types: "
        "`token` (partial LLM output), `tool_start`, `tool_end`, `done`, `error`."
    ),
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Server-Sent Events stream",
        }
    },
)
async def stream(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> StreamingResponse:
    logger.info(
        "Stream request | conversation_id=%s", request.conversation_id
    )

    async def _event_generator():
        try:
            async for chunk in agent_service.stream(request):
                payload = chunk.model_dump_json()
                yield f"data: {payload}\n\n"
        except Exception as exc:
            error_chunk = StreamChunk(
                event="error",
                data={"error": str(exc)},
                conversation_id=request.conversation_id,
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Agent service health check",
    description="Returns MCP connectivity status and the configured LLM model.",
)
async def health(
    mcp_manager: MCPClientManager = Depends(get_mcp_manager),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        mcp_connected=mcp_manager.is_connected,
        llm_model=settings.llm_model,
        version=settings.app_version,
    )
