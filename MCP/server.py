"""
FinsightAI MCP Server
=====================
FastMCP server exposing five tools:
  1. get_company_financials  – live snapshot of key financial metrics (yfinance .info)
  2. get_price_history       – historical OHLCV price data for charting
  3. get_fundamentals        – full income / balance / cashflow statements (annual & quarterly)
  4. place_order             – submit a paper-trading order via Alpaca Paper API
  5. vector_store            – add documents to / query a ChromaDB collection
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal

import pandas as pd
import requests

import chromadb
import yfinance as yf
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s – %(message)s")
logger = logging.getLogger("finsightai.mcp")

# ---------------------------------------------------------------------------
# Server initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="FinsightAI Financial MCP",
    instructions=(
        "You are a financial data assistant. "
        "Use `get_company_financials` to pull live market data for any US-listed company, "
        "and `vector_store` to persist or semantically search financial documents in ChromaDB."
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok"})

# ---------------------------------------------------------------------------
# ChromaDB client (remote HTTPS via CHROMA_URL, or local persistent fallback)
# ---------------------------------------------------------------------------

_CHROMA_URL        = os.getenv("CHROMA_URL", "")
_DEFAULT_COLLECTION = os.getenv("CHROMA_DEFAULT_COLLECTION", "stream2_sentiment")
_CF_CLIENT_ID      = os.getenv("CF-ACCESS-CLIENT-ID", "")
_CF_CLIENT_SECRET  = os.getenv("CF-ACCESS-CLIENT-SECRET", "")
_OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")


def _get_chroma_client() -> chromadb.ClientAPI:
    """Return a ChromaDB HttpClient connected to the remote ChromaDB instance.

    CHROMA_URL must be set (e.g. https://chroma.taskcomply.com).
    Cloudflare Access service-token headers are attached automatically when
    CF-ACCESS-CLIENT-ID / CF-ACCESS-CLIENT-SECRET are present in the environment.
    """
    if not _CHROMA_URL:
        raise RuntimeError(
            "CHROMA_URL is not set. "
            "Add CHROMA_URL=https://<your-chroma-host> to MCP/.env."
        )
    return chromadb.HttpClient(
        host=_CHROMA_URL,
        headers={
            "CF-Access-Client-Id":     _CF_CLIENT_ID,
            "CF-Access-Client-Secret": _CF_CLIENT_SECRET,
        },
    )


def _get_embedding_fn() -> Any:
    """
    Return an embedding function.
    Prefers OpenAI embeddings when OPENAI_API_KEY is set,
    otherwise falls back to the lightweight default (all-MiniLM-L6-v2).
    """
    # if _OPENAI_API_KEY:
    #     return embedding_functions.OpenAIEmbeddingFunction(
    #         api_key=_OPENAI_API_KEY,
    #         model_name="text-embedding-3-small",
    #     )
    return embedding_functions.DefaultEmbeddingFunction()


# ---------------------------------------------------------------------------
# Tool 1 – Yahoo Finance financial data
# ---------------------------------------------------------------------------

class FinancialDataResult(BaseModel):
    ticker: str
    company_name: str
    sector: str | None
    industry: str | None
    market_cap: float | None
    currency: str | None
    current_price: float | None
    previous_close: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    pe_ratio: float | None
    forward_pe: float | None
    price_to_book: float | None
    dividend_yield: float | None
    earnings_per_share: float | None
    revenue_ttm: float | None
    gross_profit_ttm: float | None
    ebitda: float | None
    total_debt: float | None
    total_cash: float | None
    free_cashflow: float | None
    analyst_recommendation: str | None
    target_mean_price: float | None
    description: str | None


@mcp.tool
def get_company_financials(ticker: str) -> FinancialDataResult:
    """
    Retrieve comprehensive financial data for a US-listed company from Yahoo Finance.

    Returns key metrics including market cap, price history, valuation ratios (P/E,
    P/B), profitability figures (revenue, EBITDA, free cash flow), balance-sheet items
    (total debt, cash), dividend yield, and the latest analyst recommendation.

    Args:
        ticker: The stock ticker symbol (e.g. "AAPL", "MSFT", "GOOGL").

    Returns:
        A structured object containing all available financial metrics for the company.
    """
    stock = yf.Ticker(ticker.upper())
    info: dict[str, Any] = stock.info or {}

    return FinancialDataResult(
        ticker=ticker.upper(),
        company_name=info.get("longName") or info.get("shortName") or ticker.upper(),
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=info.get("marketCap"),
        currency=info.get("currency"),
        current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
        previous_close=info.get("previousClose") or info.get("regularMarketPreviousClose"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        pe_ratio=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        price_to_book=info.get("priceToBook"),
        dividend_yield=info.get("dividendYield"),
        earnings_per_share=info.get("trailingEps"),
        revenue_ttm=info.get("totalRevenue"),
        gross_profit_ttm=info.get("grossProfits"),
        ebitda=info.get("ebitda"),
        total_debt=info.get("totalDebt"),
        total_cash=info.get("totalCash"),
        free_cashflow=info.get("freeCashflow"),
        analyst_recommendation=info.get("recommendationKey"),
        target_mean_price=info.get("targetMeanPrice"),
        description=info.get("longBusinessSummary"),
    )


# ---------------------------------------------------------------------------
# Tool 2 – Yahoo Finance historical price data
# ---------------------------------------------------------------------------

class PriceHistoryResult(BaseModel):
    ticker: str
    company_name: str
    period: str
    interval: str
    data: list[dict[str, Any]]   # [{date, open, high, low, close, volume}, …]


@mcp.tool
def get_price_history(
    ticker: str,
    period: str = "1y",
) -> PriceHistoryResult:
    """
    Fetch historical OHLCV price data for a US-listed company, ready for charting.

    The interval is automatically chosen to keep the result concise (≤ 60 rows):
      • period ≤ 3 months  → daily bars
      • period ≤ 1 year    → weekly bars
      • period  > 1 year   → monthly bars

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL", "MSFT").
        period: One of "1mo", "3mo", "6mo", "1y", "2y", "5y". Defaults to "1y".

    Returns:
        Structured price history suitable for embedding as a frontend chart block.
    """
    interval_map = {
        "1mo": "1d",
        "3mo": "1d",
        "6mo": "1wk",
        "1y":  "1wk",
        "2y":  "1mo",
        "5y":  "1mo",
    }
    interval = interval_map.get(period, "1wk")

    stock = yf.Ticker(ticker.upper())
    hist  = stock.history(period=period, interval=interval)
    info  = stock.info or {}

    data = [
        {
            "date":   str(idx.date()),
            "open":   round(float(row["Open"]),  2),
            "high":   round(float(row["High"]),  2),
            "low":    round(float(row["Low"]),   2),
            "close":  round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        for idx, row in hist.iterrows()
    ]

    return PriceHistoryResult(
        ticker=ticker.upper(),
        company_name=info.get("longName") or info.get("shortName") or ticker.upper(),
        period=period,
        interval=interval,
        data=data,
    )


# ---------------------------------------------------------------------------
# Tool 3 – Fundamental financial statements (income / balance / cash flow)
# ---------------------------------------------------------------------------

class FundamentalsResult(BaseModel):
    ticker: str
    company_name: str
    statement: str              # "income" | "balance" | "cashflow"
    frequency: str              # "annual" | "quarterly"
    periods: list[str]          # period-end dates, newest first, e.g. ["2024-09-28", …]
    rows: list[dict[str, Any]]  # [{metric, <period>: value, …}, …]
    currency: str | None


def _df_to_rows(df: pd.DataFrame) -> tuple[list[str], list[dict[str, Any]]]:
    """Convert a yfinance financial-statement DataFrame into (periods, rows)."""
    periods: list[str] = [
        str(col.date()) if hasattr(col, "date") else str(col)
        for col in df.columns
    ]
    rows: list[dict[str, Any]] = []
    for metric_name, series in df.iterrows():
        row: dict[str, Any] = {"metric": str(metric_name)}
        for col, period in zip(df.columns, periods):
            val = series[col]
            row[period] = None if pd.isna(val) else round(float(val), 2)
        rows.append(row)
    return periods, rows


@mcp.tool
def get_fundamentals(
    ticker: str,
    statement: Literal["income", "balance", "cashflow"] = "income",
    frequency: Literal["annual", "quarterly"] = "annual",
) -> FundamentalsResult:
    """
    Fetch fundamental financial statements for a US-listed company via Yahoo Finance.

    Uses the native yfinance property API:
      • annual    → ticker.income_stmt          / ticker.balance_sheet   / ticker.cashflow
      • quarterly → ticker.quarterly_income_stmt / ticker.quarterly_balance_sheet / ticker.quarterly_cashflow

    Annual mode returns up to 4 fiscal years; quarterly returns the last ~5 quarters.

    Args:
        ticker:    Stock ticker symbol (e.g. "AAPL", "MSFT", "GOOGL").
        statement: Which statement to retrieve:
                     - "income"   → Income Statement (revenue, gross profit, EBITDA, net income, EPS, …)
                     - "balance"  → Balance Sheet (assets, liabilities, equity, debt, cash, …)
                     - "cashflow" → Cash Flow Statement (operating, investing, financing cash flows, …)
                   Defaults to "income".
        frequency: Reporting period granularity:
                     - "annual"    → Last ~4 fiscal year-end snapshots (best for long-term trends)
                     - "quarterly" → Last ~5 quarters (best for recent momentum / seasonal patterns)
                   Defaults to "annual".

    Returns:
        A structured result with:
          - `periods`: ordered list of period-end dates (newest first)
          - `rows`:    one dict per line item — keys are "metric" plus each period date
          - `currency`: reporting currency (e.g. "USD")
    """
    stock = yf.Ticker(ticker.upper())

    full_info: dict[str, Any] = {}
    try:
        full_info = stock.info or {}
    except Exception:
        pass

    company_name: str = full_info.get("longName") or full_info.get("shortName") or ticker.upper()
    currency: str | None = full_info.get("currency")

    # ── Select the correct DataFrame via the property-based API ───────────
    df: pd.DataFrame | None = None
    try:
        if frequency == "annual":
            if statement == "income":
                df = stock.income_stmt
            elif statement == "balance":
                df = stock.balance_sheet
            else:
                df = stock.cashflow
        else:  # quarterly
            if statement == "income":
                df = stock.quarterly_income_stmt
            elif statement == "balance":
                df = stock.quarterly_balance_sheet
            else:
                df = stock.quarterly_cashflow
    except Exception:
        pass

    if df is None or df.empty:
        return FundamentalsResult(
            ticker=ticker.upper(),
            company_name=company_name,
            statement=statement,
            frequency=frequency,
            periods=[],
            rows=[],
            currency=currency,
        )

    periods, rows = _df_to_rows(df)

    return FundamentalsResult(
        ticker=ticker.upper(),
        company_name=company_name,
        statement=statement,
        frequency=frequency,
        periods=periods,
        rows=rows,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Tool 4 – Alpaca Paper Trading: place order
# ---------------------------------------------------------------------------

_ALPACA_KEY    = os.getenv("ALPACA_API_KEY", "")
_ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "")
_ALPACA_URL    = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")

_ALPACA_HEADERS = {
    "APCA-API-KEY-ID":     _ALPACA_KEY,
    "APCA-API-SECRET-KEY": _ALPACA_SECRET,
    "Content-Type":        "application/json",
}


class OrderResult(BaseModel):
    order_id:     str
    client_order_id: str
    ticker:       str
    side:         str          # "buy" | "sell"
    order_type:   str          # "market" | "limit" | "stop" | "stop_limit"
    qty:          float | None
    notional:     float | None  # dollar amount (mutually exclusive with qty)
    time_in_force: str
    status:       str
    filled_qty:   float | None
    filled_avg_price: float | None
    submitted_at: str | None
    message:      str          # human-readable summary


@mcp.tool
def place_order(
    ticker: str,
    side: Literal["buy", "sell"],
    order_type: Literal["market", "limit", "stop", "stop_limit"] = "market",
    qty: float | None = None,
    notional: float | None = None,
    limit_price: float | None = None,
    stop_price: float | None = None,
    time_in_force: Literal["day", "gtc", "opg", "cls", "ioc", "fok"] = "day",
) -> OrderResult:
    """
    Place a paper-trading order via the Alpaca Paper API.

    IMPORTANT: This always targets the **paper** account (https://paper-api.alpaca.markets/v2).
    No real money is involved.

    Supply either `qty` (number of shares) OR `notional` (dollar amount), not both.
    For fractional / notional orders the order_type must be "market" and time_in_force must be "day".

    Args:
        ticker:        Stock symbol (e.g. "AAPL", "TSLA").
        side:          "buy" to open a long, "sell" to close / short.
        order_type:    "market" | "limit" | "stop" | "stop_limit"  (default: "market").
        qty:           Number of shares (can be fractional, e.g. 0.5).
        notional:      Dollar amount to invest (e.g. 100.00). Mutually exclusive with qty.
        limit_price:   Required for "limit" and "stop_limit" orders.
        stop_price:    Required for "stop" and "stop_limit" orders.
        time_in_force: Order duration: "day" (default), "gtc", "opg", "cls", "ioc", "fok".

    Returns:
        OrderResult with the confirmed order details from Alpaca.
    """
    if qty is None and notional is None:
        return OrderResult(
            order_id="", client_order_id="", ticker=ticker.upper(), side=side,
            order_type=order_type, qty=None, notional=None,
            time_in_force=time_in_force, status="rejected",
            filled_qty=None, filled_avg_price=None, submitted_at=None,
            message="You must provide either `qty` (shares) or `notional` (dollar amount).",
        )

    payload: dict[str, Any] = {
        "symbol":        ticker.upper(),
        "side":          side,
        "type":          order_type,
        "time_in_force": time_in_force,
    }
    if qty is not None:
        payload["qty"] = str(qty)
    if notional is not None:
        payload["notional"] = str(notional)
    if limit_price is not None:
        payload["limit_price"] = str(limit_price)
    if stop_price is not None:
        payload["stop_price"] = str(stop_price)

    try:
        resp = requests.post(
            f"{_ALPACA_URL}/orders",
            headers=_ALPACA_HEADERS,
            json=payload,
            timeout=15,
        )
        data = resp.json()
    except Exception as exc:
        return OrderResult(
            order_id="", client_order_id="", ticker=ticker.upper(), side=side,
            order_type=order_type, qty=qty, notional=notional,
            time_in_force=time_in_force, status="error",
            filled_qty=None, filled_avg_price=None, submitted_at=None,
            message=f"Request failed: {exc}",
        )

    if resp.status_code not in (200, 201):
        return OrderResult(
            order_id="", client_order_id="", ticker=ticker.upper(), side=side,
            order_type=order_type, qty=qty, notional=notional,
            time_in_force=time_in_force, status="rejected",
            filled_qty=None, filled_avg_price=None, submitted_at=None,
            message=data.get("message", str(data)),
        )

    filled_qty = data.get("filled_qty")
    filled_avg = data.get("filled_avg_price")
    action = f"{side.upper()} {qty or notional} {'shares' if qty else 'USD'} of {ticker.upper()}"
    summary = (
        f"Paper order placed: {action}. "
        f"Status: {data.get('status', 'unknown')}. "
        f"Order ID: {data.get('id', '')}."
    )

    return OrderResult(
        order_id=data.get("id", ""),
        client_order_id=data.get("client_order_id", ""),
        ticker=ticker.upper(),
        side=side,
        order_type=order_type,
        qty=float(qty) if qty is not None else None,
        notional=float(notional) if notional is not None else None,
        time_in_force=time_in_force,
        status=data.get("status", "unknown"),
        filled_qty=float(filled_qty) if filled_qty else None,
        filled_avg_price=float(filled_avg) if filled_avg else None,
        submitted_at=data.get("submitted_at"),
        message=summary,
    )


# ---------------------------------------------------------------------------
# Tool 5 – Chroma vector store (add / query)
# ---------------------------------------------------------------------------

class VectorStoreInput(BaseModel):
    operation: Literal["add", "query"] = Field(
        description=(
            "Operation to perform on the collection: "
            "'add' to insert new documents, 'query' to semantic-search existing ones."
        )
    )
    collection_name: str = Field(
        default=_DEFAULT_COLLECTION,
        description="Name of the ChromaDB collection to target.",
    )

    # --- add-specific fields ---
    documents: list[str] | None = Field(
        default=None,
        description="[add only] List of document texts to store.",
    )
    ids: list[str] | None = Field(
        default=None,
        description=(
            "[add only] Unique IDs for each document. "
            "Auto-generated as 'doc_0', 'doc_1', … when omitted."
        ),
    )
    metadatas: list[dict[str, Any]] | None = Field(
        default=None,
        description="[add only] Optional metadata dict for each document (same length as documents).",
    )

    # --- query-specific fields ---
    query_text: str | None = Field(
        default=None,
        description="[query only] Natural-language query to search for semantically similar documents.",
    )
    ticker: str | None = Field(
        default=None,
        description=(
            "[query only] Stock ticker symbol to filter results by (e.g. 'AAPL', 'TSLA'). "
            "When provided, only documents whose metadata 'ticker' field matches this value are returned."
        ),
    )
    n_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="[query only] Maximum number of results to return.",
    )
    where: dict[str, Any] | None = Field(
        default=None,
        description=(
            "[query only] Optional metadata filter (ChromaDB where-clause syntax). "
            "If 'ticker' is also provided, the two filters are merged with $and."
        ),
    )


class VectorStoreResult(BaseModel):
    operation: str
    collection_name: str
    message: str
    data: list[dict[str, Any]] | None = None


@mcp.tool
def vector_store(params: VectorStoreInput) -> VectorStoreResult:
    """
    Interact with a ChromaDB vector store to manage and search financial documents.

    Supports two operations:
    • **add**   – Embed and persist one or more text documents into the specified collection,
                  optionally attaching metadata (e.g. ticker, date, source).
    • **query** – Run a semantic similarity search against stored documents and return
                  the top-N most relevant results together with their metadata and
                  distance scores.

    Args:
        params: A VectorStoreInput object specifying the operation and its parameters.

    Returns:
        A VectorStoreResult with a status message and (for queries) the matching documents.
    """
    logger.info(
        "vector_store called | operation=%s | collection=%s | ticker=%s",
        params.operation,
        params.collection_name,
        params.ticker or "—",
    )

    client = _get_chroma_client()
    embed_fn = _get_embedding_fn()

    # ---- ADD ---------------------------------------------------------------
    if params.operation == "add":
        collection = client.get_or_create_collection(
            name=params.collection_name,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

        if not params.documents:
            logger.warning("vector_store [add] | no documents provided")
            return VectorStoreResult(
                operation="add",
                collection_name=params.collection_name,
                message="No documents provided. Pass at least one document in the 'documents' field.",
            )

        doc_ids = params.ids or [f"doc_{i}" for i in range(len(params.documents))]
        metadatas = params.metadatas or [{}] * len(params.documents)

        logger.info(
            "vector_store [add] | collection=%s | doc_count=%d | ids=%s",
            params.collection_name,
            len(params.documents),
            doc_ids,
        )

        collection.add(
            ids=doc_ids,
            documents=params.documents,
            metadatas=metadatas,
        )

        logger.info(
            "vector_store [add] | success | collection=%s | added=%d",
            params.collection_name,
            len(params.documents),
        )

        return VectorStoreResult(
            operation="add",
            collection_name=params.collection_name,
            message=(
                f"Successfully added {len(params.documents)} document(s) "
                f"to collection '{params.collection_name}'."
            ),
            data=[
                {"id": did, "document_preview": doc[:120] + ("…" if len(doc) > 120 else "")}
                for did, doc in zip(doc_ids, params.documents)
            ],
        )

    # ---- QUERY -------------------------------------------------------------
    if not params.query_text:
        logger.warning("vector_store [query] | no query_text provided")
        return VectorStoreResult(
            operation="query",
            collection_name=params.collection_name,
            message="No query_text provided. Pass a search string in the 'query_text' field.",
        )

    collection = client.get_collection(
        name=params.collection_name,
        embedding_function=embed_fn,
    )

    # Build the where-clause: ticker filter + any extra where clause
    ticker_filter: dict[str, Any] | None = (
        {"ticker": params.ticker.upper()} if params.ticker else None
    )
    if ticker_filter and params.where:
        effective_where: dict[str, Any] | None = {"$and": [ticker_filter, params.where]}
    elif ticker_filter:
        effective_where = ticker_filter
    else:
        effective_where = params.where

    logger.info(
        "vector_store [query] | collection=%s | query='%s' | ticker=%s | where=%s | n_results=%d",
        params.collection_name,
        params.query_text,
        params.ticker or "—",
        effective_where,
        params.n_results,
    )

    query_kwargs: dict[str, Any] = {
        "query_texts": [params.query_text],
        "n_results": min(params.n_results, collection.count() or params.n_results),
        "include": ["documents", "metadatas", "distances"],
    }
    if effective_where:
        query_kwargs["where"] = effective_where

    results = collection.query(**query_kwargs)

    hits: list[dict[str, Any]] = []
    ids_list = results.get("ids", [[]])[0]
    docs_list = results.get("documents", [[]])[0]
    meta_list = results.get("metadatas", [[]])[0]
    dist_list = results.get("distances", [[]])[0]

    for doc_id, doc, meta, dist in zip(ids_list, docs_list, meta_list, dist_list):
        hits.append(
            {
                "id": doc_id,
                "document": doc,
                "metadata": meta,
                "similarity_score": round(1 - dist, 4),
            }
        )

    logger.info(
        "vector_store [query] | results=%d | top_score=%s | ids=%s",
        len(hits),
        hits[0]["similarity_score"] if hits else "n/a",
        [h["id"] for h in hits],
    )

    return VectorStoreResult(
        operation="query",
        collection_name=params.collection_name,
        message=f"Found {len(hits)} result(s) for query: '{params.query_text}'.",
        data=hits,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    port = int(os.getenv("MCP_PORT", "8080"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    if transport == "http":
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()
