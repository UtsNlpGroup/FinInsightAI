"""
Dependency Injection providers for FastAPI.

Pattern: Dependency Injection
  FastAPI's `Depends()` mechanism is used to resolve services at request time.
  All singletons (settings, MCP manager, agent service) live on `app.state`
  and are surfaced via these provider functions, keeping routes decoupled from
  construction logic.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.agent_service import AgentService
from app.services.mcp_manager import MCPClientManager


def get_mcp_manager(request: Request) -> MCPClientManager:
    """Resolve the MCPClientManager stored on app.state."""
    return request.app.state.mcp_manager


def get_agent_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AgentService:
    """
    Resolve the AgentService.

    A new AgentService is constructed per-request so it always receives the
    current MCPClientManager (which may have refreshed its tool list).
    Construction is cheap because the expensive parts (LLM init, graph compile)
    happen lazily inside service methods.
    """
    mcp_manager: MCPClientManager = request.app.state.mcp_manager
    return AgentService(mcp_manager=mcp_manager, settings=settings)
