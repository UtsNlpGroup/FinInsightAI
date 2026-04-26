"""
Unit tests for backend/app/services/analysis_service.py helper functions.

Tests the JSON extraction helpers (_extract_json_array, _extract_json_object,
_parse_disclosure_insight_cards, _filing_risk_to_insight_card) and the
DisclosureInsightCard impact_level validator.
"""

import pytest

from app.services.analysis_service import (
    _extract_json_array,
    _extract_json_object,
    _filing_risk_to_insight_card,
    _parse_disclosure_insight_cards,
)
from app.schemas.analysis import DisclosureInsightCard, FilingRisk


# ── _extract_json_array ───────────────────────────────────────────────────────

class TestExtractJsonArray:
    """Handles direct JSON, fenced JSON, and embedded JSON inside preamble text."""

    def test_parses_clean_json_array(self):
        text = '[{"title": "Risk A", "description": "desc", "category": "Regulatory"}]'
        result = _extract_json_array(text)
        assert isinstance(result, list)
        assert result[0]["title"] == "Risk A"

    def test_parses_array_inside_markdown_fence(self):
        text = '```json\n[{"title": "T1"}]\n```'
        result = _extract_json_array(text)
        assert len(result) == 1

    def test_parses_array_after_preamble_text(self):
        text = 'Here are the risks:\n[{"title": "T1"}, {"title": "T2"}]'
        result = _extract_json_array(text)
        assert len(result) == 2

    def test_returns_empty_list_for_invalid_json(self):
        result = _extract_json_array("This is not JSON at all.")
        assert result == []

    def test_returns_empty_list_for_json_object_not_array(self):
        result = _extract_json_array('{"key": "value"}')
        assert result == []

    def test_handles_multi_item_array(self):
        items = [{"title": f"Risk {i}"} for i in range(5)]
        import json
        result = _extract_json_array(json.dumps(items))
        assert len(result) == 5

    def test_strips_whitespace_before_parsing(self):
        text = '   \n[{"x": 1}]\n   '
        result = _extract_json_array(text)
        assert result[0]["x"] == 1

    def test_handles_code_fence_without_json_tag(self):
        text = '```\n[{"title": "T1"}]\n```'
        result = _extract_json_array(text)
        assert len(result) == 1


# ── _extract_json_object ──────────────────────────────────────────────────────

class TestExtractJsonObject:
    """Handles direct dicts, fenced dicts, and embedded dicts."""

    def test_parses_clean_json_object(self):
        text = '{"outlook": "Strong growth", "tags": ["AI", "Services"]}'
        result = _extract_json_object(text)
        assert result["outlook"] == "Strong growth"
        assert result["tags"] == ["AI", "Services"]

    def test_parses_object_inside_fence(self):
        text = '```json\n{"outlook": "Positive", "tags": []}\n```'
        result = _extract_json_object(text)
        assert result["outlook"] == "Positive"

    def test_extracts_object_embedded_in_text(self):
        text = 'The result is: {"outlook": "Neutral", "tags": ["Risk"]}'
        result = _extract_json_object(text)
        assert result is not None
        assert "outlook" in result

    def test_returns_none_for_plain_text(self):
        result = _extract_json_object("No JSON here at all.")
        assert result is None

    def test_returns_none_for_json_array(self):
        result = _extract_json_object("[1, 2, 3]")
        assert result is None


# ── _parse_disclosure_insight_cards ──────────────────────────────────────────

class TestParseDisclosureInsightCards:
    """Verify malformed items are skipped and valid ones are parsed."""

    def test_valid_array_produces_cards(self):
        text = '''[
          {"title": "T1", "description": "D1", "impact": "HIGH", "impact_level": "high", "icon": "⚠️", "page_ref": "MD&A"},
          {"title": "T2", "description": "D2", "impact": "MED",  "impact_level": "medium", "icon": "📈", "page_ref": "Item 7"}
        ]'''
        cards = _parse_disclosure_insight_cards(text)
        assert len(cards) == 2
        assert cards[0].title == "T1"

    def test_malformed_item_skipped(self):
        text = '''[
          {"title": "Valid Card", "description": "ok", "impact": "HIGH", "impact_level": "high", "icon": "⚠️"},
          "not a dict"
        ]'''
        cards = _parse_disclosure_insight_cards(text)
        assert len(cards) == 1

    def test_empty_array_returns_empty_list(self):
        cards = _parse_disclosure_insight_cards("[]")
        assert cards == []

    def test_invalid_text_returns_empty_list(self):
        cards = _parse_disclosure_insight_cards("no json here")
        assert cards == []


# ── _filing_risk_to_insight_card ─────────────────────────────────────────────

class TestFilingRiskToInsightCard:
    """Verify FilingRisk → DisclosureInsightCard mapping."""

    def test_regulatory_risk_maps_to_high_impact(self):
        risk = FilingRisk(title="Antitrust Action", description="Regulatory scrutiny.", category="Regulatory")
        card = _filing_risk_to_insight_card(risk)
        assert card.impact_level == "high"
        assert "HIGH" in card.impact

    def test_market_risk_maps_to_medium_impact(self):
        risk = FilingRisk(title="Competition", description="Increased competition.", category="Market")
        card = _filing_risk_to_insight_card(risk)
        assert card.impact_level == "medium"

    def test_unknown_category_defaults_to_medium(self):
        risk = FilingRisk(title="Some Risk", description="Unknown category risk.", category=None)
        card = _filing_risk_to_insight_card(risk)
        assert card.impact_level == "medium"

    def test_card_has_warning_emoji(self):
        risk = FilingRisk(title="T", description="D", category="Financial")
        card = _filing_risk_to_insight_card(risk)
        assert card.icon == "⚠️"

    def test_card_page_ref_includes_item_1a(self):
        risk = FilingRisk(title="T", description="D", category="Legal")
        card = _filing_risk_to_insight_card(risk)
        assert "1A" in card.page_ref or "1a" in card.page_ref.lower()

    def test_card_title_matches_risk_title(self):
        risk = FilingRisk(title="Supply Chain Disruption", description="D.", category="Operational")
        card = _filing_risk_to_insight_card(risk)
        assert card.title == "Supply Chain Disruption"


# ── DisclosureInsightCard impact_level validator ──────────────────────────────

class TestDisclosureInsightCardImpactLevelValidator:
    """Verify the validator normalises and coerces impact_level values."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("high", "high"),
            ("HIGH", "high"),
            ("medium", "medium"),
            ("low", "low"),
            ("positive_high", "positive_high"),
            ("positive-high", "positive_high"),
            ("positive_medium", "positive_medium"),
            (None, "medium"),
            ("completely_unknown", "medium"),
        ],
    )
    def test_impact_level_normalisation(self, raw, expected):
        card = DisclosureInsightCard(
            title="T",
            description="D",
            impact="IMPACT",
            impact_level=raw,
        )
        assert card.impact_level == expected
