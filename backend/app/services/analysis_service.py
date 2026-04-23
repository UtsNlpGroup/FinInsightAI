"""
AnalysisService – structured 10-K analysis powered by the LangGraph agent.

Wraps AgentService with two specialised operations that use carefully crafted
prompts to produce consistent, structured outputs instead of free-form chat.

Both methods:
  1. Build a prompt that instructs the agent to use the vector_store and
     get_company_financials MCP tools to ground its answer in real data.
  2. Call AgentService.chat() and post-process the raw LLM text into the
     required response schema.
"""

from __future__ import annotations

import json
import logging
import re
from uuid import uuid4

from app.schemas.agent import ChatRequest
from app.schemas.analysis import (
    AIThemesResponse,
    FilingRisk,
    FilingRisksResponse,
    MarketNewsItem,
    MarketNewsResponse,
    OverallOutlookResponse,
    SentimentBreakdown,
    SentimentDivergenceResponse,
)
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)


# ── Prompt templates ──────────────────────────────────────────────────────────

_OUTLOOK_PROMPT = """You are a senior financial analyst.

For the company with ticker {ticker}:
1. Use the vector_store tool with collection_name="sec_filings", query_text="10-K highlights strategic initiatives financial performance {ticker}", n_results=5 to retrieve key filing content.
2. Use get_company_financials to get current market data and analyst sentiment.

Then write EXACTLY ONE sentence (maximum 45 words) that synthesises:
- The company's internal 10-K highlights (growth drivers, financial strengths, strategic initiatives)
- External market sentiment, key risks, or headwinds

Follow this pattern:
"While [Company] highlights [internal positives] in their 10-K, [external market context / risks / sentiment]."

Return ONLY the single sentence. No preamble, no explanation, no line breaks."""

_RISKS_PROMPT = """You are a senior financial analyst performing a risk assessment.

For the company with ticker {ticker}:
1. Use the vector_store tool with collection_name="sec_filings", query_text="risk factors challenges threats {ticker} 10-K", n_results=8 to retrieve risk-related content from the filing.
2. Use get_company_financials to enrich the picture with current market context if relevant.

Extract the 5–8 most significant risk factors mentioned or implied. Return them as a JSON array with this EXACT structure — no other text, no markdown fences:

[
  {{"title": "Short Risk Title", "description": "One to two sentence description of the risk.", "category": "Category"}},
  ...
]

Valid categories: Regulatory, Market, Operational, Financial, Geopolitical, Technology, Competition, Legal.

Return ONLY the raw JSON array."""

_AI_THEMES_PROMPT = """You are a senior financial analyst.

For the company with ticker {ticker}:
1. Use the vector_store tool with collection_name="stream2_sentiment", query_text="themes trends topics {ticker} news analysis outlook", ticker="{ticker}", n_results=15 to retrieve recent news and sentiment data.

From the retrieved documents, extract 5–8 recurring themes, topics, or narratives that dominate the coverage (e.g. "Services Growth", "AI Integration", "Margin Pressure", "Antitrust Risk", "FSD Update").

Return ONLY a raw JSON array of short theme strings (2–4 words each) — no preamble, no markdown fences:

["Theme One", "Theme Two", ...]"""

_SENTIMENT_DIVERGENCE_PROMPT = """You are a senior financial analyst.

For the company with ticker {ticker}:
1. Use the vector_store tool with collection_name="stream2_sentiment", query_text="{ticker} market sentiment news analysis", ticker="{ticker}", n_results=20 to retrieve a broad set of news and sentiment data.

Count the total number of documents retrieved. For each document, classify its sentiment as "bullish", "neutral", or "bearish" based on its content and any sentiment metadata.

Calculate the percentage of documents in each category (percentages must sum to 100).

Return ONLY a raw JSON array with exactly three items in this order — no preamble, no markdown fences:

[
  {{"label": "Bullish",  "percentage": <integer 0-100>, "sentiment": "bullish"}},
  {{"label": "Neutral",  "percentage": <integer 0-100>, "sentiment": "neutral"}},
  {{"label": "Bearish",  "percentage": <integer 0-100>, "sentiment": "bearish"}}
]

The three percentages must add up to 100. If no documents are found, return equal thirds (34, 33, 33)."""

_MARKET_NEWS_PROMPT = """You are a senior financial analyst.

For the company with ticker {ticker}:
1. Use the vector_store tool with collection_name="stream2_sentiment", query_text="{ticker} latest news headlines market updates", ticker="{ticker}", n_results=8 to retrieve recent news items.

For each document returned, extract:
- title: the headline or main topic (from the document text)
- summary: one sentence summarising the key point
- sentiment: "bullish", "bearish", or "neutral" (infer from the document text and metadata)
- source: the news source from metadata, uppercased (e.g. "BLOOMBERG"); omit if absent
- time_ago: human-readable relative time if a date is in metadata (e.g. "2H AGO", "1D AGO"); omit if absent
- url: article URL from metadata; omit if absent

Return ONLY a raw JSON array — no preamble, no markdown fences:

[
  {{"title": "...", "summary": "...", "sentiment": "bullish", "source": "BLOOMBERG", "time_ago": "2H AGO", "url": "https://..."}},
  ...
]"""


# ── JSON extraction helper ────────────────────────────────────────────────────

def _extract_json_array(text: str) -> list[dict]:
    """
    Try to parse a JSON array from LLM output.
    Handles cases where the model wraps the array in markdown fences or
    adds a short preamble before the '['.
    """
    text = text.strip()

    # 1. Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences and retry
    fenced = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)
    try:
        result = json.loads(fenced.strip())
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 3. Find the first '[...]' block in the text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []


# ── Service ───────────────────────────────────────────────────────────────────

class AnalysisService:
    """
    Provides structured 10-K analysis operations.

    Delegates the actual LLM + MCP tool execution to AgentService and
    post-processes the results into typed response objects.
    """

    def __init__(self, agent_service: AgentService) -> None:
        self._agent = agent_service

    async def get_overall_outlook(self, ticker: str) -> OverallOutlookResponse:
        """
        Generate a single-sentence outlook for *ticker* that combines the
        company's 10-K highlights with external market sentiment.
        """
        ticker = ticker.upper().strip()
        prompt = _OUTLOOK_PROMPT.format(ticker=ticker)

        logger.info("AnalysisService.get_overall_outlook | ticker=%s", ticker)
        response = await self._agent.chat(
            ChatRequest(message=prompt, conversation_id=str(uuid4()))
        )

        # Clean up any stray whitespace / newlines from the LLM
        outlook = response.answer.strip().replace("\n", " ")

        return OverallOutlookResponse(
            ticker=ticker,
            outlook=outlook,
            tool_calls=response.tool_calls,
        )

    async def get_filing_risks(self, ticker: str) -> FilingRisksResponse:
        """
        Extract and return the main risk factors from *ticker*'s 10-K filing.
        """
        ticker = ticker.upper().strip()
        prompt = _RISKS_PROMPT.format(ticker=ticker)

        logger.info("AnalysisService.get_filing_risks | ticker=%s", ticker)
        response = await self._agent.chat(
            ChatRequest(message=prompt, conversation_id=str(uuid4()))
        )

        raw_items = _extract_json_array(response.answer)
        risks: list[FilingRisk] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                risks.append(FilingRisk.model_validate(item))
            except Exception:
                # Skip malformed items but keep the rest
                logger.warning("Skipping malformed risk item: %s", item)

        if not risks:
            logger.warning(
                "AnalysisService.get_filing_risks: no risks parsed for %s; "
                "raw answer: %.300s",
                ticker,
                response.answer,
            )

        return FilingRisksResponse(
            ticker=ticker,
            risks=risks,
            tool_calls=response.tool_calls,
        )

    async def get_ai_themes(self, ticker: str) -> AIThemesResponse:
        """Extract recurring AI/market themes from recent news for *ticker*."""
        ticker = ticker.upper().strip()
        prompt = _AI_THEMES_PROMPT.format(ticker=ticker)

        logger.info("AnalysisService.get_ai_themes | ticker=%s", ticker)
        response = await self._agent.chat(
            ChatRequest(message=prompt, conversation_id=str(uuid4()))
        )

        raw = _extract_json_array(response.answer)
        themes = [str(t).strip() for t in raw if isinstance(t, str) and t.strip()]

        if not themes:
            logger.warning(
                "AnalysisService.get_ai_themes: no themes parsed for %s; "
                "raw answer: %.300s",
                ticker,
                response.answer,
            )

        return AIThemesResponse(
            ticker=ticker,
            themes=themes,
            tool_calls=response.tool_calls,
        )

    async def get_sentiment_divergence(self, ticker: str) -> SentimentDivergenceResponse:
        """Return institutional vs social sentiment breakdown for *ticker*."""
        ticker = ticker.upper().strip()
        prompt = _SENTIMENT_DIVERGENCE_PROMPT.format(ticker=ticker)

        logger.info("AnalysisService.get_sentiment_divergence | ticker=%s", ticker)
        response = await self._agent.chat(
            ChatRequest(message=prompt, conversation_id=str(uuid4()))
        )

        raw = _extract_json_array(response.answer)
        breakdown: list[SentimentBreakdown] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                breakdown.append(SentimentBreakdown.model_validate(item))
            except Exception:
                logger.warning("Skipping malformed breakdown item: %s", item)

        if not breakdown:
            logger.warning(
                "AnalysisService.get_sentiment_divergence: no breakdown parsed for %s; "
                "raw answer: %.300s",
                ticker,
                response.answer,
            )

        return SentimentDivergenceResponse(
            ticker=ticker,
            breakdown=breakdown,
            tool_calls=response.tool_calls,
        )

    async def get_market_news(self, ticker: str) -> MarketNewsResponse:
        """Return recent news items from the sentiment collection for *ticker*."""
        ticker = ticker.upper().strip()
        prompt = _MARKET_NEWS_PROMPT.format(ticker=ticker)

        logger.info("AnalysisService.get_market_news | ticker=%s", ticker)
        response = await self._agent.chat(
            ChatRequest(message=prompt, conversation_id=str(uuid4()))
        )

        raw = _extract_json_array(response.answer)
        items: list[MarketNewsItem] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                items.append(MarketNewsItem.model_validate(item))
            except Exception:
                logger.warning("Skipping malformed news item: %s", item)

        if not items:
            logger.warning(
                "AnalysisService.get_market_news: no items parsed for %s; "
                "raw answer: %.300s",
                ticker,
                response.answer,
            )

        return MarketNewsResponse(
            ticker=ticker,
            items=items,
            tool_calls=response.tool_calls,
        )
