"""
Alpaca Paper Trading endpoints.

All calls target the **paper** account only:
  https://paper-api.alpaca.markets/v2

Endpoints:
  GET /alpaca/positions  – list of current open positions
  GET /alpaca/account    – paper account overview (equity, cash, buying power, P&L)
  GET /alpaca/orders     – recent orders (open + filled)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alpaca", tags=["Alpaca Paper Trading"])

_ALPACA_BASE = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")
_ALPACA_KEY  = os.getenv("ALPACA_API_KEY",  "")
_ALPACA_SEC  = os.getenv("ALPACA_SECRET_KEY", "")

_HEADERS = {
    "APCA-API-KEY-ID":     _ALPACA_KEY,
    "APCA-API-SECRET-KEY": _ALPACA_SEC,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _alpaca_get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Fire a GET request to the Alpaca paper API and return parsed JSON."""
    url = f"{_ALPACA_BASE}{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=_HEADERS, params=params)
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Alpaca authentication failed – check API keys.")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── Schemas ───────────────────────────────────────────────────────────────────

class Position(BaseModel):
    asset_id:       str
    symbol:         str
    exchange:       str | None
    asset_class:    str | None
    qty:            float
    qty_available:  float
    side:           str           # "long" | "short"
    market_value:   float | None
    cost_basis:     float | None
    unrealized_pl:  float | None
    unrealized_plpc: float | None  # percentage
    current_price:  float | None
    avg_entry_price: float | None
    change_today:   float | None  # day P&L %


class AccountSummary(BaseModel):
    id:              str
    status:          str
    currency:        str
    cash:            float
    buying_power:    float
    portfolio_value: float
    equity:          float
    last_equity:     float
    long_market_value:  float
    short_market_value: float
    daytrade_count:  int
    pattern_day_trader: bool


class Order(BaseModel):
    id:              str
    client_order_id: str
    symbol:          str
    side:            str
    order_type:      str
    qty:             float | None
    notional:        float | None
    filled_qty:      float | None
    filled_avg_price: float | None
    status:          str
    time_in_force:   str
    submitted_at:    str | None
    filled_at:       str | None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/positions",
    response_model=list[Position],
    summary="Open positions in the Alpaca paper account",
)
async def get_positions() -> list[Position]:
    """Return all currently open positions in the paper account."""
    raw: list[dict] = await _alpaca_get("/positions")
    return [
        Position(
            asset_id=p.get("asset_id", ""),
            symbol=p.get("symbol", ""),
            exchange=p.get("exchange"),
            asset_class=p.get("asset_class"),
            qty=float(p.get("qty", 0)),
            qty_available=float(p.get("qty_available", 0)),
            side=p.get("side", "long"),
            market_value=_f(p.get("market_value")),
            cost_basis=_f(p.get("cost_basis")),
            unrealized_pl=_f(p.get("unrealized_pl")),
            unrealized_plpc=_f(p.get("unrealized_plpc")),
            current_price=_f(p.get("current_price")),
            avg_entry_price=_f(p.get("avg_entry_price")),
            change_today=_f(p.get("change_today")),
        )
        for p in raw
    ]


@router.get(
    "/account",
    response_model=AccountSummary,
    summary="Paper account overview (equity, cash, buying power)",
)
async def get_account() -> AccountSummary:
    """Return key account metrics for the Alpaca paper account."""
    a: dict = await _alpaca_get("/account")
    return AccountSummary(
        id=a.get("id", ""),
        status=a.get("status", ""),
        currency=a.get("currency", "USD"),
        cash=float(a.get("cash", 0)),
        buying_power=float(a.get("buying_power", 0)),
        portfolio_value=float(a.get("portfolio_value", 0)),
        equity=float(a.get("equity", 0)),
        last_equity=float(a.get("last_equity", 0)),
        long_market_value=float(a.get("long_market_value", 0)),
        short_market_value=float(a.get("short_market_value", 0)),
        daytrade_count=int(a.get("daytrade_count", 0)),
        pattern_day_trader=bool(a.get("pattern_day_trader", False)),
    )


@router.get(
    "/orders",
    response_model=list[Order],
    summary="Recent orders from the Alpaca paper account",
)
async def get_orders(
    status: str = Query(default="all", description="Filter by status: 'open', 'closed', or 'all'"),
    limit:  int = Query(default=50, ge=1, le=500, description="Max number of orders to return"),
) -> list[Order]:
    """Return recent orders (open and/or filled) from the paper account."""
    raw: list[dict] = await _alpaca_get("/orders", params={"status": status, "limit": limit})
    return [
        Order(
            id=o.get("id", ""),
            client_order_id=o.get("client_order_id", ""),
            symbol=o.get("symbol", ""),
            side=o.get("side", ""),
            order_type=o.get("type", ""),
            qty=_f(o.get("qty")),
            notional=_f(o.get("notional")),
            filled_qty=_f(o.get("filled_qty")),
            filled_avg_price=_f(o.get("filled_avg_price")),
            status=o.get("status", ""),
            time_in_force=o.get("time_in_force", ""),
            submitted_at=o.get("submitted_at"),
            filled_at=o.get("filled_at"),
        )
        for o in raw
    ]


# ── Utility ───────────────────────────────────────────────────────────────────

def _f(v: Any) -> float | None:
    """Safely coerce a value to float, returning None for missing/null."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
