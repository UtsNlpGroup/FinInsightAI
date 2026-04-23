"""
Pydantic schemas for the Analysis endpoints.

These endpoints use the LangGraph agent to produce structured summaries
directly from 10-K filing data retrieved via the MCP vector-store tool.
"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

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
    tags: list[str] = Field(
        default_factory=list,
        description="Short theme labels (e.g. for UI chips) derived from the synthesis.",
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


# ── Disclosure insight cards (dashboard / 10-K tabs) ──────────────────────────

_IMPACT_LEVELS = frozenset({"high", "medium", "low", "positive_high", "positive_medium"})


class DisclosureInsightCard(BaseModel):
    """One card for risks, growth, or capex insight lists."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    title: str = Field(description="Short card title.")
    page_ref: str = Field(
        default="10-K",
        validation_alias=AliasChoices("page_ref", "pageRef"),
        description="Filing section reference if known.",
    )
    description: str = Field(description="One-to-two sentence summary.")
    impact: str = Field(description="Badge label, e.g. HIGH IMPACT.")
    impact_level: str = Field(
        default="medium",
        validation_alias=AliasChoices("impact_level", "impactLevel"),
        description="One of: high, medium, low, positive_high, positive_medium.",
    )
    icon: str = Field(default="📄", description="Single emoji.")

    @field_validator("impact_level", mode="before")
    @classmethod
    def normalize_impact_level(cls, v: object) -> str:
        if v is None:
            return "medium"
        s = str(v).lower().replace("-", "_").strip()
        if s in _IMPACT_LEVELS:
            return s
        if "positive" in s and "high" in s:
            return "positive_high"
        if "positive" in s:
            return "positive_medium"
        return "medium"


class DisclosureInsightsResponse(BaseModel):
    """Returned by GET /analysis/risks|growth-strategies|capex/{ticker}."""

    ticker: str = Field(description="Ticker symbol (upper-cased).")
    cards: list[DisclosureInsightCard] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


# ── AI Themes ─────────────────────────────────────────────────────────────────

class AIThemesResponse(BaseModel):
    """Returned by GET /analysis/ai-themes/{ticker}."""

    ticker: str = Field(description="Ticker symbol (upper-cased).")
    themes: list[str] = Field(
        default_factory=list,
        description="Recurring themes and narratives extracted from recent news (2–4 words each).",
    )
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


# ── Sentiment Divergence ──────────────────────────────────────────────────────

class SentimentBreakdown(BaseModel):
    """Sentiment breakdown for one source category."""

    label: str = Field(description="Source category label, e.g. 'Institutional Focus'.")
    percentage: int = Field(description="Percentage (0–100) of documents with the dominant sentiment.")
    sentiment: str = Field(description="Dominant sentiment: 'positive', 'negative', or 'neutral'.")


class SentimentDivergenceResponse(BaseModel):
    """Returned by GET /analysis/sentiment-divergence/{ticker}."""

    ticker: str = Field(description="Ticker symbol (upper-cased).")
    breakdown: list[SentimentBreakdown] = Field(
        default_factory=list,
        description="Sentiment breakdown by source category (Institutional vs Social).",
    )
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


# ── Market News ───────────────────────────────────────────────────────────────

class MarketNewsItem(BaseModel):
    """A single news item for the Market Sentiment news feed."""

    title: str = Field(description="Headline or main topic of the article.")
    summary: str = Field(description="One sentence summary of the key point.")
    sentiment: str = Field(description="'bullish', 'bearish', or 'neutral'.")
    source: str | None = Field(default=None, description="News source, uppercased (e.g. 'BLOOMBERG').")
    time_ago: str | None = Field(default=None, description="Human-readable relative time (e.g. '2H AGO').")
    url: str | None = Field(default=None, description="Article URL.")


class MarketNewsResponse(BaseModel):
    """Returned by GET /analysis/market-news/{ticker}."""

    ticker: str = Field(description="Ticker symbol (upper-cased).")
    items: list[MarketNewsItem] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
