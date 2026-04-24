"""
Analysis endpoints – v1.

Two agent-powered GET endpoints under /api/v1/analysis:

  GET /outlook/{ticker}
    Returns one sentence synthesising the company's 10-K highlights with
    external market sentiment. Example:
    "While Apple highlights robust services growth in their 10-K, external
     sentiment remains cautious over antitrust scrutiny and supply-chain risk."

  GET /filing-risks/{ticker}
    Returns a structured list of the main risk factors extracted from the 10-K
    (title, description, category per risk).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.dependencies import get_analysis_service
from app.schemas.analysis import (
    AIThemesResponse,
    DisclosureInsightsResponse,
    FilingRisksResponse,
    MarketNewsResponse,
    OverallOutlookResponse,
    SentimentDivergenceResponse,
)
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ── GET /outlook/{ticker} ─────────────────────────────────────────────────────

@router.get(
    "/outlook/{ticker}",
    response_model=OverallOutlookResponse,
    summary="Get overall 10-K outlook for a ticker",
    description=(
        "Uses the financial agent to query the 10-K vector store and live "
        "market data, then produces a single sentence combining the company's "
        "internal highlights with external market sentiment."
    ),
)
async def get_overall_outlook(
    ticker: str = Path(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol, e.g. AAPL.",
    ),
    svc: AnalysisService = Depends(get_analysis_service),
) -> OverallOutlookResponse:
    logger.info("GET /analysis/outlook/%s", ticker)
    try:
        return await svc.get_overall_outlook(ticker)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/outlook/%s", ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate outlook.",
        ) from exc


# ── GET /filing-risks/{ticker} ────────────────────────────────────────────────

@router.get(
    "/filing-risks/{ticker}",
    response_model=FilingRisksResponse,
    summary="Get main risk factors from the 10-K filing",
    description=(
        "Uses the financial agent to search the 10-K vector store for risk "
        "factors and returns a structured list with title, description, and "
        "category for each risk."
    ),
)
async def get_filing_risks(
    ticker: str = Path(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol, e.g. AAPL.",
    ),
    svc: AnalysisService = Depends(get_analysis_service),
) -> FilingRisksResponse:
    logger.info("GET /analysis/filing-risks/%s", ticker)
    try:
        return await svc.get_filing_risks(ticker)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/filing-risks/%s", ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract filing risks.",
        ) from exc


# ── GET /risks/{ticker} ─────────────────────────────────────────────────────────

@router.get(
    "/risks/{ticker}",
    response_model=DisclosureInsightsResponse,
    summary="10-K risk factors as dashboard cards",
    description=(
        "Runs the same filing-risk extraction as /filing-risks and maps results "
        "to title, description, impact badges, and icons for UI cards."
    ),
)
async def get_risk_insights(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL."),
    svc: AnalysisService = Depends(get_analysis_service),
) -> DisclosureInsightsResponse:
    logger.info("GET /analysis/risks/%s", ticker)
    try:
        return await svc.get_risk_insights(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/risks/%s", ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load risk insights.",
        ) from exc


# ── GET /growth-strategies/{ticker} ─────────────────────────────────────────────

@router.get(
    "/growth-strategies/{ticker}",
    response_model=DisclosureInsightsResponse,
    summary="Growth and strategy insights from the 10-K",
    description="Queries sec_filings for growth drivers, expansion, and strategic initiatives.",
)
async def get_growth_strategy_insights(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL."),
    svc: AnalysisService = Depends(get_analysis_service),
) -> DisclosureInsightsResponse:
    logger.info("GET /analysis/growth-strategies/%s", ticker)
    try:
        return await svc.get_growth_strategy_insights(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/growth-strategies/%s", ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load growth strategy insights.",
        ) from exc


# ── GET /capex/{ticker} ───────────────────────────────────────────────────────

@router.get(
    "/capex/{ticker}",
    response_model=DisclosureInsightsResponse,
    summary="CapEx and investment insights from the 10-K",
    description="Queries sec_filings for capital expenditures, PP&E, and investing cash flows.",
)
async def get_capex_insights(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL."),
    svc: AnalysisService = Depends(get_analysis_service),
) -> DisclosureInsightsResponse:
    logger.info("GET /analysis/capex/%s", ticker)
    try:
        return await svc.get_capex_insights(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/capex/%s", ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load CapEx insights.",
        ) from exc


# ── GET /ai-themes/{ticker} ───────────────────────────────────────────────────

@router.get(
    "/ai-themes/{ticker}",
    response_model=AIThemesResponse,
    summary="Extract recurring AI/market themes from recent news",
    description=(
        "Queries the news collection and returns 5–8 recurring "
        "themes or narratives found in recent coverage of the ticker "
        "(e.g. 'Services Growth', 'AI Integration', 'Margin Pressure')."
    ),
)
async def get_ai_themes(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL."),
    svc: AnalysisService = Depends(get_analysis_service),
) -> AIThemesResponse:
    logger.info("GET /analysis/ai-themes/%s", ticker)
    try:
        return await svc.get_ai_themes(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/ai-themes/%s", ticker)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to extract AI themes.") from exc


# ── GET /sentiment-divergence/{ticker} ────────────────────────────────────────

@router.get(
    "/sentiment-divergence/{ticker}",
    response_model=SentimentDivergenceResponse,
    summary="Get institutional vs social sentiment divergence",
    description=(
        "Queries the news collection with a large result set and "
        "returns a breakdown of dominant sentiment by source category "
        "(Institutional Focus vs Social Sentiment), each with a percentage."
    ),
)
async def get_sentiment_divergence(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL."),
    svc: AnalysisService = Depends(get_analysis_service),
) -> SentimentDivergenceResponse:
    logger.info("GET /analysis/sentiment-divergence/%s", ticker)
    try:
        return await svc.get_sentiment_divergence(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/sentiment-divergence/%s", ticker)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compute sentiment divergence.") from exc


# ── GET /market-news/{ticker} ─────────────────────────────────────────────────

@router.get(
    "/market-news/{ticker}",
    response_model=MarketNewsResponse,
    summary="Get recent news items for the Market Sentiment feed",
    description=(
        "Queries the news collection and returns up to 8 recent "
        "news items with title, summary, sentiment, source, relative time, and URL."
    ),
)
async def get_market_news(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL."),
    svc: AnalysisService = Depends(get_analysis_service),
) -> MarketNewsResponse:
    logger.info("GET /analysis/market-news/%s", ticker)
    try:
        return await svc.get_market_news(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error in /analysis/market-news/%s", ticker)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch market news.") from exc
