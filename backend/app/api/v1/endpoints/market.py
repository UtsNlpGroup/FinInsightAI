"""
Market data endpoints.

Provides a lightweight REST API for:
  • GET /market/price/{ticker}   – real-time stock quote via Yahoo Finance
  • GET /market/prices/batch     – batch quotes + sparklines for all tracked tickers
  • GET /market/companies        – list of tracked companies from Supabase
  • POST /market/companies       – add a new company to track
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class StockQuote(BaseModel):
    ticker: str
    company_name: str
    price: float | None
    previous_close: float | None
    change: float | None
    change_pct: float | None
    currency: str | None
    market_state: str | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None


class Company(BaseModel):
    ticker: str
    company_name: str
    sector: str | None


class AddCompanyRequest(BaseModel):
    ticker: str
    company_name: str
    sector: str | None = None


class TickerBandItem(BaseModel):
    ticker: str
    company_name: str
    price: float | None
    change: float | None
    change_pct: float | None
    currency: str | None = "USD"
    sparkline: list[float] = []


# ── Simple in-process TTL cache (60 s) ────────────────────────────────────────
_band_cache: dict[str, tuple[list[TickerBandItem], float]] = {}
_CACHE_TTL = 60.0


def _cache_get(key: str) -> list[TickerBandItem] | None:
    entry = _band_cache.get(key)
    if entry and (time.time() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None


def _cache_set(key: str, data: list[TickerBandItem]) -> None:
    _band_cache[key] = (data, time.time())


# ── Synchronous yfinance batch fetch (runs in thread-pool) ────────────────────

def _sync_batch_fetch(
    tickers: list[str],
    name_map: dict[str, str],
) -> list[TickerBandItem]:
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        return []

    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="7d",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        logger.warning("yfinance batch download failed: %s", exc)
        return []

    result: list[TickerBandItem] = []
    for t in tickers:
        try:
            # Column layout differs for single vs multiple tickers
            if len(tickers) == 1:
                closes = data["Close"].dropna().values.tolist()
            else:
                col = data["Close"]
                if t not in col.columns:
                    continue
                closes = col[t].dropna().values.tolist()

            if not closes:
                continue

            price   = closes[-1]
            prev    = closes[-2] if len(closes) >= 2 else closes[0]
            change  = round(price - prev, 4) if prev else None
            chg_pct = round((change / prev) * 100, 4) if change and prev else None
            spark   = [round(float(v), 2) for v in (closes[-6:] if len(closes) >= 6 else closes)]

            result.append(
                TickerBandItem(
                    ticker=t,
                    company_name=name_map.get(t, t),
                    price=round(float(price), 2),
                    change=change,
                    change_pct=chg_pct,
                    currency="USD",
                    sparkline=spark,
                )
            )
        except Exception as exc:
            logger.debug("Skipping %s in batch: %s", t, exc)

    return result


# ── Companies endpoints ────────────────────────────────────────────────────────

@router.get(
    "/companies",
    response_model=list[Company],
    summary="List all tracked companies",
)
async def list_companies() -> list[Company]:
    """Return every company stored in the `public.companies` table, ordered by ticker."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select ticker, company_name, sector from public.companies order by ticker"
        )
    return [Company(ticker=r["ticker"], company_name=r["company_name"], sector=r["sector"]) for r in rows]


@router.post(
    "/companies",
    response_model=Company,
    status_code=201,
    summary="Add a new company to track",
)
async def add_company(body: AddCompanyRequest) -> Company:
    """
    Insert a company into `public.companies`.
    If the ticker already exists, updates `company_name` and `sector`.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            insert into public.companies (ticker, company_name, sector)
            values ($1, $2, $3)
            on conflict (ticker) do update
                set company_name = excluded.company_name,
                    sector       = excluded.sector
            returning ticker, company_name, sector
            """,
            body.ticker.strip().upper(),
            body.company_name.strip(),
            body.sector,
        )
    return Company(ticker=row["ticker"], company_name=row["company_name"], sector=row["sector"])


# ── Batch prices endpoint (ticker band) ────────────────────────────────────────

@router.get(
    "/prices/batch",
    response_model=list[TickerBandItem],
    summary="Batch quotes + 6-day sparklines for all tracked companies",
)
async def batch_prices() -> list[TickerBandItem]:
    """
    Fetch closing-price history (last 7 days, daily) for every company in
    `public.companies` using a single yfinance download call.

    Results are cached for 60 seconds to avoid hammering Yahoo Finance.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select ticker, company_name from public.companies order by ticker"
        )

    if not rows:
        return []

    tickers  = [r["ticker"] for r in rows]
    name_map = {r["ticker"]: r["company_name"] for r in rows}
    cache_key = ",".join(sorted(tickers))

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_batch_fetch, tickers, name_map)

    _cache_set(cache_key, result)
    return result


# ── Single price endpoint ──────────────────────────────────────────────────────

@router.get(
    "/price/{ticker}",
    response_model=StockQuote,
    summary="Get the current price and basic quote data for a stock ticker",
)
async def get_price(ticker: str) -> StockQuote:
    """
    Fetch a real-time quote for *ticker* via Yahoo Finance.

    Returns the current price, previous close, absolute and percentage
    change, and 52-week high/low.  Response is typically < 200 ms.
    """
    try:
        import yfinance as yf  # imported lazily to avoid slow module-level load

        symbol = ticker.strip().upper()
        stock  = yf.Ticker(symbol)
        info: dict[str, Any] = stock.info or {}

        if not info:
            raise HTTPException(status_code=404, detail=f"No data found for ticker '{symbol}'")

        price          = info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        change     = round(price - previous_close, 4) if price and previous_close else None
        change_pct = round((change / previous_close) * 100, 4) if change and previous_close else None

        return StockQuote(
            ticker=symbol,
            company_name=info.get("longName") or info.get("shortName") or symbol,
            price=price,
            previous_close=previous_close,
            change=change,
            change_pct=change_pct,
            currency=info.get("currency"),
            market_state=info.get("marketState"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch quote for %s: %s", ticker, exc)
        raise HTTPException(status_code=502, detail=f"Could not fetch quote for '{ticker}': {exc}") from exc
