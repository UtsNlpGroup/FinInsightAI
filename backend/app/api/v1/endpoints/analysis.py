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
from app.schemas.analysis import FilingRisksResponse, OverallOutlookResponse
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
