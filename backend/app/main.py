"""
FastAPI application factory.

Pattern: Application Factory
  `create_app()` constructs and configures the FastAPI instance.
  This makes the app easily testable (each test can call create_app()
  with overridden settings) and deployable without import-time side-effects.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.core.config import Settings, get_settings
from app.core.database import close_pool
from app.services.mcp_manager import MCPClientManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler (startup → yield → shutdown).

    Connects the MCP client on startup and disconnects on shutdown.
    Storing the manager on `app.state` makes it accessible to dependencies
    without relying on module-level globals.
    """
    settings: Settings = app.state.settings

    logger.info("Starting %s v%s [%s]", settings.app_name, settings.app_version, settings.environment)

    # ── MCP client ────────────────────────────────────────────────────────
    mcp_manager = MCPClientManager(settings)
    app.state.mcp_manager = mcp_manager
    await mcp_manager.connect()

    yield

    logger.info("Shutting down …")
    await mcp_manager.disconnect()
    await close_pool()


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Construct and return the FastAPI application.

    Args:
        settings: Optional Settings override (useful in tests).
    """
    cfg = settings or get_settings()

    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description=(
            "FinsightAI Backend – a LangGraph-powered financial agent that "
            "uses Yahoo Finance and ChromaDB through an MCP server."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Attach settings to app state so the lifespan and dependencies can read it
    app.state.settings = cfg

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(v1_router)

    # ── Root health check (lightweight, no dependencies) ─────────────────────
    @app.get("/health", tags=["Health"], summary="Application liveness probe")
    async def root_health():
        return {"status": "ok", "version": cfg.app_version}

    logger.info("Routes registered: %s", [r.path for r in app.routes])
    return app


# Uvicorn / Gunicorn entry point
app = create_app()
