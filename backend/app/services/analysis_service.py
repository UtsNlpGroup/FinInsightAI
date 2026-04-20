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
    FilingRisk,
    FilingRisksResponse,
    OverallOutlookResponse,
)
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)


# ── Prompt templates ──────────────────────────────────────────────────────────

_OUTLOOK_PROMPT = """You are a senior financial analyst.

For the company with ticker {ticker}:
1. Use the vector_store tool (operation="query", query="10-K highlights strategic initiatives financial performance {ticker}") to retrieve key filing content.
2. Use get_company_financials to get current market data and analyst sentiment.

Then write EXACTLY ONE sentence (maximum 45 words) that synthesises:
- The company's internal 10-K highlights (growth drivers, financial strengths, strategic initiatives)
- External market sentiment, key risks, or headwinds

Follow this pattern:
"While [Company] highlights [internal positives] in their 10-K, [external market context / risks / sentiment]."

Return ONLY the single sentence. No preamble, no explanation, no line breaks."""

_RISKS_PROMPT = """You are a senior financial analyst performing a risk assessment.

For the company with ticker {ticker}:
1. Use the vector_store tool (operation="query", query="risk factors challenges threats {ticker} 10-K") to retrieve risk-related content from the filing.
2. Use get_company_financials to enrich the picture with current market context if relevant.

Extract the 5–8 most significant risk factors mentioned or implied. Return them as a JSON array with this EXACT structure — no other text, no markdown fences:

[
  {{"title": "Short Risk Title", "description": "One to two sentence description of the risk.", "category": "Category"}},
  ...
]

Valid categories: Regulatory, Market, Operational, Financial, Geopolitical, Technology, Competition, Legal.

Return ONLY the raw JSON array."""


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
