"""
Async PostgreSQL connection pool (Supabase direct connection via asyncpg).

Public API
----------
get_pool()   – returns the shared asyncpg Pool (creates it on first call)
close_pool() – gracefully closes the pool (called on app shutdown)
"""

from __future__ import annotations

import asyncio
import logging
import socket
import ssl as _ssl
import urllib.parse
from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from asyncpg import Pool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool: "Pool | None" = None

# ── Pool management ───────────────────────────────────────────────────────────

async def get_pool() -> "Pool":
    global _pool
    if _pool is None:
        dsn = get_settings().supabase_db_url
        if not dsn:
            raise RuntimeError(
                "SUPABASE_DB_URL is not set. "
                "Add it to backend/.env or as an environment variable."
            )

        pool_kwargs: dict = {
            "min_size": 1,
            "max_size": 5,
            "command_timeout": 30,
            "statement_cache_size": 0,
        }

        # Docker's default bridge network has no IPv6 routing, so if the
        # pooler hostname resolves to an AAAA record the OS raises Errno 99
        # ("Cannot assign requested address").  We try IPv4 first; if that
        # yields nothing we fall back to any address family but still prefer
        # IPv4 so we don't hand asyncpg an unreachable IPv6 literal.
        parsed = urllib.parse.urlparse(dsn)
        hostname = parsed.hostname or ""
        port = parsed.port or 5432

        def _resolve_preferred_ip(host: str, p: int) -> str:
            """Return the best routable IP for *host*: prefer IPv4, accept IPv6."""
            # 1) Try IPv4-only first
            try:
                infos = socket.getaddrinfo(host, p, socket.AF_INET, socket.SOCK_STREAM)
                if infos:
                    return infos[0][4][0]
            except OSError:
                pass
            # 2) Any address family — pick the first IPv4 we find, else first IPv6
            infos = socket.getaddrinfo(host, p, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ipv4_hits = [i[4][0] for i in infos if i[0] == socket.AF_INET]
            if ipv4_hits:
                return ipv4_hits[0]
            return infos[0][4][0]  # IPv6 as last resort

        try:
            loop = asyncio.get_event_loop()
            resolved_ip = await loop.run_in_executor(
                None, lambda: _resolve_preferred_ip(hostname, port)
            )

            # We connect via a raw IP so hostname validation is impossible.
            # Supabase's pooler also uses an intermediate CA not in the default
            # bundle, so we enable SSL transport but skip certificate checks.
            ssl_ctx = _ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = _ssl.CERT_NONE

            pool_kwargs.update({
                "host": resolved_ip,
                "port": port,
                "user": parsed.username,
                "password": urllib.parse.unquote(parsed.password or ""),
                "database": (parsed.path or "/postgres").lstrip("/"),
                "ssl": ssl_ctx,
            })
            logger.info("Resolved %s → %s", hostname, resolved_ip)
        except Exception as exc:
            logger.warning("IP resolution failed (%s) – falling back to plain DSN", exc)
            pool_kwargs["dsn"] = dsn

        _pool = await asyncpg.create_pool(**pool_kwargs)
        logger.info("Database pool created (Supabase Postgres)")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")

