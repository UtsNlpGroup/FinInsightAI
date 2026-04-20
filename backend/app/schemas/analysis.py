"""
Pydantic schemas for the Analysis endpoints.

These endpoints use the LangGraph agent to produce structured summaries
directly from 10-K filing data retrieved via the MCP vector-store tool.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.agent import ToolCallTrace


# ── Overall Outlook ───────────────────────────────────────────────────────────

class OverallOutlookResponse(BaseModel):
    """Returned by GET /analysis/outlook/{ticker}."""

    ticker: str = Field(description="Ticker symbol (upper-cased).")
    outlook: str = Field(
        description=(
            "One concise sentence synthesising the company's 10-K highlights "
            "with external market sentiment and key risks."
        )
    )
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


# ── Filing Risks ──────────────────────────────────────────────────────────────

class FilingRisk(BaseModel):
    """A single risk factor extracted from the 10-K."""

    title: str = Field(description="Short risk title (3–7 words).")
    description: str = Field(description="One-to-two sentence explanation.")
    category: str | None = Field(
        default=None,
        description=(
            "Risk category, e.g. Regulatory, Market, Operational, Financial, "
            "Geopolitical, Technology, Competition, Legal."
        ),
    )


class FilingRisksResponse(BaseModel):
    """Returned by GET /analysis/filing-risks/{ticker}."""

    ticker: str = Field(description="Ticker symbol (upper-cased).")
    risks: list[FilingRisk] = Field(
        default_factory=list,
        description="Ordered list of key risk factors found in the 10-K.",
    )
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
