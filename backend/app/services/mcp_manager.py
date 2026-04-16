"""
MCPClientManager – Singleton that owns the lifecycle of the
langchain-mcp-adapters MultiServerMCPClient connection.

Pattern: Singleton + Context-Manager adapter
  The manager is instantiated once at application startup (via FastAPI lifespan)
  and torn down on shutdown, ensuring a single shared MCP session per process.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import Settings

logger = logging.getLogger(__name__)


class MCPClientManager:
    """
    Manages a persistent connection to the FinsightAI MCP server.

    Responsibilities:
    - Open / close the underlying MultiServerMCPClient session.
    - Cache loaded tools so every agent invocation reuses the same objects.
    - Expose a readiness flag so the health endpoint can report truthfully.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: MultiServerMCPClient | None = None
        self._tools: list[BaseTool] = []
        self._connected: bool = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """
        Open the MCP client session and pre-load all available tools.
        Called once during application startup (FastAPI lifespan).
        """
        logger.info("Connecting to MCP server at %s …", self._settings.mcp_server_url)
        self._client = MultiServerMCPClient(
            {
                "finsight": {
                    "url": self._settings.mcp_server_url,
                    "transport": "http",
                }
            }
        )
        try:
            self._tools = await self._client.get_tools()
            self._connected = True
            logger.info(
                "MCP connection established. %d tool(s) loaded: %s",
                len(self._tools),
                [t.name for t in self._tools],
            )
        except Exception as exc:
            self._connected = False
            logger.error("Failed to connect to MCP server: %s", exc)
            raise

    async def disconnect(self) -> None:
        """Release the MCP session. Called on application shutdown."""
        self._tools = []
        self._connected = False
        self._client = None
        logger.info("MCP client disconnected.")

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_tools(self) -> list[BaseTool]:
        """Return the cached list of LangChain tools backed by MCP."""
        if not self._connected or not self._tools:
            raise RuntimeError(
                "MCP client is not connected. "
                "Ensure connect() was called during application startup."
            )
        return self._tools

    async def refresh_tools(self) -> list[BaseTool]:
        """Re-fetch tools from the MCP server (useful after server restarts)."""
        if self._client is None:
            raise RuntimeError("MCP client has not been initialised.")
        self._tools = await self._client.get_tools()
        logger.info("MCP tools refreshed: %s", [t.name for t in self._tools])
        return self._tools
