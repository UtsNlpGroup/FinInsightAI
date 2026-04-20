"""
FinsightAI MCP Server
=====================
FastMCP server exposing two tools:
  1. get_company_financials  – fetches live financial data via Yahoo Finance
  2. vector_store            – adds documents to / queries a Chroma collection
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal

import chromadb
import yfinance as yf
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field

load_dotenv()

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

_CHROMA_URL = os.getenv("CHROMA_URL", "")
_CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
_DEFAULT_COLLECTION = os.getenv("CHROMA_DEFAULT_COLLECTION", "stream2_sentiment")

_CF_CLIENT_ID = os.getenv("CF-ACCESS-CLIENT-ID", "")
_CF_CLIENT_SECRET = os.getenv("CF-ACCESS-CLIENT-SECRET", "")

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _get_chroma_client() -> chromadb.ClientAPI:
    """Return a ChromaDB client based on environment configuration.

    When CHROMA_URL is set the server connects to the remote ChromaDB instance.
    Provide the full URL including scheme, e.g. https://chroma.taskcomply.com.
    Cloudflare Access service-token headers are attached automatically when the
    corresponding env vars are present.
    """
    if _CHROMA_URL:
        return chromadb.HttpClient(
            host=_CHROMA_URL,
            headers={
                "CF-Access-Client-Id": _CF_CLIENT_ID,
                "CF-Access-Client-Secret": _CF_CLIENT_SECRET,
            },
        )
    return chromadb.PersistentClient(path=_CHROMA_PERSIST_DIR)


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
# Tool 3 – Chroma vector store (add / query)
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
    n_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="[query only] Maximum number of results to return.",
    )
    where: dict[str, Any] | None = Field(
        default=None,
        description="[query only] Optional metadata filter (ChromaDB where-clause syntax).",
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
    client = _get_chroma_client()
    embed_fn = _get_embedding_fn()

    collection = client.get_or_create_collection(
        name=params.collection_name,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # ---- ADD ---------------------------------------------------------------
    if params.operation == "add":
        if not params.documents:
            return VectorStoreResult(
                operation="add",
                collection_name=params.collection_name,
                message="No documents provided. Pass at least one document in the 'documents' field.",
            )

        doc_ids = params.ids or [f"doc_{i}" for i in range(len(params.documents))]
        metadatas = params.metadatas or [{}] * len(params.documents)

        collection.add(
            ids=doc_ids,
            documents=params.documents,
            metadatas=metadatas,
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
        return VectorStoreResult(
            operation="query",
            collection_name=params.collection_name,
            message="No query_text provided. Pass a search string in the 'query_text' field.",
        )

    query_kwargs: dict[str, Any] = {
        "query_texts": [params.query_text],
        "n_results": min(params.n_results, collection.count() or params.n_results),
        "include": ["documents", "metadatas", "distances"],
    }
    if params.where:
        query_kwargs["where"] = params.where

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
