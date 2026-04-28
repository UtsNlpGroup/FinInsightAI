"""
API contract tests for /api/v1/analysis/* endpoints.

Every analysis route returns a structured response driven by the agent.
With the mock AnalysisService (from conftest), responses are predictable
so we test schema shape, ticker uppercasing, and error handling.
"""

from __future__ import annotations

import pytest


TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]


# ── GET /api/v1/analysis/outlook/{ticker} ─────────────────────────────────────

@pytest.mark.api
class TestOutlookEndpoint:

    def test_returns_200_for_valid_ticker(self, client):
        resp = client.get("/api/v1/analysis/outlook/AAPL")
        assert resp.status_code == 200

    def test_response_has_outlook_field(self, client):
        resp = client.get("/api/v1/analysis/outlook/AAPL")
        body = resp.json()
        assert "outlook" in body
        assert isinstance(body["outlook"], str)
        assert len(body["outlook"]) > 0

    def test_response_has_ticker_field(self, client):
        resp = client.get("/api/v1/analysis/outlook/AAPL")
        assert resp.json()["ticker"] == "AAPL"

    def test_response_has_tags_list(self, client):
        resp = client.get("/api/v1/analysis/outlook/AAPL")
        body = resp.json()
        assert "tags" in body
        assert isinstance(body["tags"], list)

    def test_response_has_tool_calls_list(self, client):
        resp = client.get("/api/v1/analysis/outlook/AAPL")
        assert isinstance(resp.json().get("tool_calls"), list)

    @pytest.mark.parametrize("ticker", TICKERS)
    def test_multiple_tickers_return_200(self, client, ticker):
        resp = client.get(f"/api/v1/analysis/outlook/{ticker}")
        assert resp.status_code == 200


# ── GET /api/v1/analysis/filing-risks/{ticker} ────────────────────────────────

@pytest.mark.api
class TestFilingRisksEndpoint:

    def test_returns_200_for_valid_ticker(self, client):
        resp = client.get("/api/v1/analysis/filing-risks/AAPL")
        assert resp.status_code == 200

    def test_response_has_risks_list(self, client):
        resp = client.get("/api/v1/analysis/filing-risks/AAPL")
        body = resp.json()
        assert "risks" in body
        assert isinstance(body["risks"], list)

    def test_risk_has_title_description_category(self, client):
        resp = client.get("/api/v1/analysis/filing-risks/AAPL")
        risks = resp.json()["risks"]
        if risks:
            for risk in risks:
                assert "title" in risk
                assert "description" in risk

    def test_ticker_in_response(self, client):
        resp = client.get("/api/v1/analysis/filing-risks/MSFT")
        assert resp.json()["ticker"] == "MSFT"


# ── GET /api/v1/analysis/risks/{ticker} ───────────────────────────────────────

@pytest.mark.api
class TestRiskInsightsEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/v1/analysis/risks/AAPL").status_code == 200

    def test_response_has_cards_list(self, client):
        resp = client.get("/api/v1/analysis/risks/AAPL")
        assert "cards" in resp.json()

    def test_card_has_required_fields(self, client):
        resp = client.get("/api/v1/analysis/risks/AAPL")
        for card in resp.json().get("cards", []):
            assert "title" in card
            assert "description" in card
            assert "impact" in card
            assert "impact_level" in card

    def test_impact_level_is_valid(self, client):
        valid_levels = {"high", "medium", "low", "positive_high", "positive_medium"}
        resp = client.get("/api/v1/analysis/risks/AAPL")
        for card in resp.json().get("cards", []):
            assert card["impact_level"] in valid_levels


# ── GET /api/v1/analysis/growth-strategies/{ticker} ──────────────────────────

@pytest.mark.api
class TestGrowthStrategiesEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/v1/analysis/growth-strategies/AAPL").status_code == 200

    def test_response_has_cards_with_positive_impact(self, client):
        resp = client.get("/api/v1/analysis/growth-strategies/AAPL")
        cards = resp.json().get("cards", [])
        assert len(cards) > 0

    def test_ticker_in_response(self, client):
        resp = client.get("/api/v1/analysis/growth-strategies/NVDA")
        assert resp.json()["ticker"] == "NVDA"


# ── GET /api/v1/analysis/capex/{ticker} ───────────────────────────────────────

@pytest.mark.api
class TestCapexEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/v1/analysis/capex/AAPL").status_code == 200

    def test_response_has_cards(self, client):
        resp = client.get("/api/v1/analysis/capex/AAPL")
        assert "cards" in resp.json()

    def test_card_has_page_ref(self, client):
        resp = client.get("/api/v1/analysis/capex/AAPL")
        for card in resp.json().get("cards", []):
            assert "page_ref" in card


# ── GET /api/v1/analysis/ai-themes/{ticker} ───────────────────────────────────

@pytest.mark.api
class TestAIThemesEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/v1/analysis/ai-themes/AAPL").status_code == 200

    def test_response_has_themes_list(self, client):
        resp = client.get("/api/v1/analysis/ai-themes/AAPL")
        assert "themes" in resp.json()
        assert isinstance(resp.json()["themes"], list)

    def test_themes_are_strings(self, client):
        resp = client.get("/api/v1/analysis/ai-themes/AAPL")
        for theme in resp.json()["themes"]:
            assert isinstance(theme, str)


# ── GET /api/v1/analysis/sentiment-divergence/{ticker} ────────────────────────

@pytest.mark.api
class TestSentimentDivergenceEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/v1/analysis/sentiment-divergence/AAPL").status_code == 200

    def test_response_has_breakdown_list(self, client):
        resp = client.get("/api/v1/analysis/sentiment-divergence/AAPL")
        assert "breakdown" in resp.json()
        assert isinstance(resp.json()["breakdown"], list)

    def test_breakdown_items_have_percentage_and_sentiment(self, client):
        resp = client.get("/api/v1/analysis/sentiment-divergence/AAPL")
        for item in resp.json().get("breakdown", []):
            assert "percentage" in item
            assert "sentiment" in item
            assert isinstance(item["percentage"], int)

    def test_percentages_sum_to_100(self, client):
        resp = client.get("/api/v1/analysis/sentiment-divergence/AAPL")
        total = sum(b["percentage"] for b in resp.json().get("breakdown", []))
        assert total == 100


# ── GET /api/v1/analysis/market-news/{ticker} ─────────────────────────────────

@pytest.mark.api
class TestMarketNewsEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/v1/analysis/market-news/AAPL").status_code == 200

    def test_response_has_items_list(self, client):
        resp = client.get("/api/v1/analysis/market-news/AAPL")
        assert "items" in resp.json()
        assert isinstance(resp.json()["items"], list)

    def test_news_item_has_required_fields(self, client):
        resp = client.get("/api/v1/analysis/market-news/AAPL")
        for item in resp.json().get("items", []):
            assert "title" in item
            assert "summary" in item
            assert "sentiment" in item

    def test_sentiment_values_are_valid(self, client):
        valid_sentiments = {"bullish", "bearish", "neutral"}
        resp = client.get("/api/v1/analysis/market-news/AAPL")
        for item in resp.json().get("items", []):
            assert item["sentiment"] in valid_sentiments


# ── Ticker validation ─────────────────────────────────────────────────────────

@pytest.mark.api
class TestTickerValidation:
    """Tickers exceeding the 10-char max or being empty should be rejected."""

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/analysis/outlook/",
        "/api/v1/analysis/filing-risks/",
        "/api/v1/analysis/risks/",
        "/api/v1/analysis/ai-themes/",
    ])
    def test_too_long_ticker_returns_422(self, client, endpoint):
        resp = client.get(endpoint + "TOOLONGTICKER")  # 13 chars
        assert resp.status_code == 422
