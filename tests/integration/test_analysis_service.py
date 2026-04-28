"""
Integration tests for backend/app/services/analysis_service.py.

Tests that AnalysisService correctly orchestrates AgentService calls
and parses structured JSON responses into typed response models.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.schemas.agent import ChatResponse, ToolCallTrace
from app.schemas.analysis import (
    AIThemesResponse,
    DisclosureInsightsResponse,
    FilingRisksResponse,
    MarketNewsResponse,
    OverallOutlookResponse,
    SentimentDivergenceResponse,
)
from app.services.analysis_service import AnalysisService


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _agent_response(answer: str) -> ChatResponse:
    return ChatResponse(conversation_id="test-id", answer=answer, tool_calls=[], input_tokens=50, output_tokens=80)


@pytest.fixture
def mock_agent_svc() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def svc(mock_agent_svc) -> AnalysisService:
    return AnalysisService(agent_service=mock_agent_svc)


# ── get_overall_outlook ───────────────────────────────────────────────────────

@pytest.mark.integration
class TestGetOverallOutlook:

    @pytest.mark.asyncio
    async def test_returns_outlook_response_type(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response(
            '{"outlook": "While Apple highlights services growth, regulatory risk persists.", "tags": ["Services", "Regulatory", "AI"]}'
        )
        result = await svc.get_overall_outlook("AAPL")
        assert isinstance(result, OverallOutlookResponse)

    @pytest.mark.asyncio
    async def test_ticker_is_uppercased(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response(
            '{"outlook": "Outlook.", "tags": ["T1", "T2", "T3"]}'
        )
        result = await svc.get_overall_outlook("aapl")
        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_tags_extracted_from_json(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response(
            '{"outlook": "Strong outlook.", "tags": ["AI Growth", "Services", "CapEx"]}'
        )
        result = await svc.get_overall_outlook("AAPL")
        assert "AI Growth" in result.tags
        assert len(result.tags) == 3

    @pytest.mark.asyncio
    async def test_falls_back_to_raw_text_when_json_fails(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response("Plain text outlook fallback.")
        result = await svc.get_overall_outlook("MSFT")
        assert "Plain text" in result.outlook
        assert result.tags == []

    @pytest.mark.asyncio
    async def test_agent_called_once_with_message(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response('{"outlook": "ok", "tags": []}')
        await svc.get_overall_outlook("NVDA")
        mock_agent_svc.chat.assert_called_once()
        call_arg = mock_agent_svc.chat.call_args[0][0]
        assert "NVDA" in call_arg.message


# ── get_filing_risks ──────────────────────────────────────────────────────────

@pytest.mark.integration
class TestGetFilingRisks:

    @pytest.mark.asyncio
    async def test_returns_filing_risks_response_type(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response(
            '[{"title": "Regulatory Risk", "description": "EU antitrust.", "category": "Regulatory"}]'
        )
        result = await svc.get_filing_risks("AAPL")
        assert isinstance(result, FilingRisksResponse)

    @pytest.mark.asyncio
    async def test_parses_multiple_risks(self, svc, mock_agent_svc):
        risks_json = json.dumps([
            {"title": "Regulatory Risk", "description": "desc1", "category": "Regulatory"},
            {"title": "Market Risk", "description": "desc2", "category": "Market"},
            {"title": "Tech Risk", "description": "desc3", "category": "Technology"},
        ])
        mock_agent_svc.chat.return_value = _agent_response(risks_json)
        result = await svc.get_filing_risks("AAPL")
        assert len(result.risks) == 3

    @pytest.mark.asyncio
    async def test_empty_when_llm_returns_no_valid_json(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response("I could not find risk factors.")
        result = await svc.get_filing_risks("AAPL")
        assert result.risks == []

    @pytest.mark.asyncio
    async def test_skips_malformed_risk_items(self, svc, mock_agent_svc):
        risks_json = '[{"title": "Valid Risk", "description": "desc", "category": "Market"}, "bad item"]'
        mock_agent_svc.chat.return_value = _agent_response(risks_json)
        result = await svc.get_filing_risks("AAPL")
        assert len(result.risks) == 1


# ── get_ai_themes ─────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestGetAIThemes:

    @pytest.mark.asyncio
    async def test_returns_ai_themes_response(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response(
            '["AI Integration", "Services Growth", "Antitrust Risk"]'
        )
        result = await svc.get_ai_themes("AAPL")
        assert isinstance(result, AIThemesResponse)
        assert len(result.themes) == 3

    @pytest.mark.asyncio
    async def test_themes_are_strings(self, svc, mock_agent_svc):
        mock_agent_svc.chat.return_value = _agent_response('["Theme A", "Theme B"]')
        result = await svc.get_ai_themes("TSLA")
        for theme in result.themes:
            assert isinstance(theme, str)


# ── get_sentiment_divergence ──────────────────────────────────────────────────

@pytest.mark.integration
class TestGetSentimentDivergence:

    @pytest.mark.asyncio
    async def test_returns_sentiment_divergence_response(self, svc, mock_agent_svc):
        divergence_json = json.dumps([
            {"label": "Bullish", "percentage": 60, "sentiment": "bullish"},
            {"label": "Neutral", "percentage": 30, "sentiment": "neutral"},
            {"label": "Bearish", "percentage": 10, "sentiment": "bearish"},
        ])
        mock_agent_svc.chat.return_value = _agent_response(divergence_json)
        result = await svc.get_sentiment_divergence("AAPL")
        assert isinstance(result, SentimentDivergenceResponse)
        assert len(result.breakdown) == 3

    @pytest.mark.asyncio
    async def test_percentages_present_in_breakdown(self, svc, mock_agent_svc):
        divergence_json = json.dumps([
            {"label": "Bullish", "percentage": 50, "sentiment": "bullish"},
            {"label": "Neutral", "percentage": 30, "sentiment": "neutral"},
            {"label": "Bearish", "percentage": 20, "sentiment": "bearish"},
        ])
        mock_agent_svc.chat.return_value = _agent_response(divergence_json)
        result = await svc.get_sentiment_divergence("NVDA")
        percentages = [b.percentage for b in result.breakdown]
        assert sum(percentages) == 100


# ── get_market_news ────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestGetMarketNews:

    @pytest.mark.asyncio
    async def test_returns_market_news_response(self, svc, mock_agent_svc):
        news_json = json.dumps([
            {
                "title": "Apple Q4 Beats Estimates",
                "summary": "Revenue exceeded Wall Street expectations.",
                "sentiment": "bullish",
                "source": "REUTERS",
                "time_ago": "3H AGO",
            }
        ])
        mock_agent_svc.chat.return_value = _agent_response(news_json)
        result = await svc.get_market_news("AAPL")
        assert isinstance(result, MarketNewsResponse)
        assert len(result.items) == 1
        assert result.items[0].sentiment == "bullish"

    @pytest.mark.asyncio
    async def test_skips_malformed_news_items(self, svc, mock_agent_svc):
        news_json = '[{"title": "Valid", "summary": "ok", "sentiment": "neutral"}, "bad"]'
        mock_agent_svc.chat.return_value = _agent_response(news_json)
        result = await svc.get_market_news("AAPL")
        assert len(result.items) == 1
