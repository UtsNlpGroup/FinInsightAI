"""
Unit tests for MCP/server.py tool helper functions and input validation.

Tests the pure helper _df_to_rows and the input validation logic in
place_order (no-qty-no-notional guard) without real HTTP calls.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sys
import os

# Make MCP importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../MCP"))

from server import _df_to_rows, OrderResult


# ── _df_to_rows ───────────────────────────────────────────────────────────────

class TestDfToRows:
    """Verify DataFrame → (periods, rows) conversion."""

    def _sample_df(self) -> pd.DataFrame:
        """Small income statement DataFrame matching yfinance structure."""
        periods = pd.to_datetime(["2024-09-28", "2023-09-30", "2022-09-24"])
        data = {
            "Total Revenue":   [391_035_000_000, 383_285_000_000, 394_328_000_000],
            "Net Income":      [93_736_000_000,  96_995_000_000,  99_803_000_000],
            "Gross Profit":    [180_683_000_000, 169_148_000_000, 170_782_000_000],
        }
        df = pd.DataFrame(data, index=list(data.keys())).T
        df.index = periods
        df.index.name = None
        # yfinance returns metric as rows and periods as columns
        return df.T

    def test_periods_are_string_dates(self):
        df = self._sample_df()
        periods, _ = _df_to_rows(df)
        for p in periods:
            assert isinstance(p, str)
            assert len(p) == 10  # "YYYY-MM-DD"

    def test_periods_ordered_newest_first(self):
        df = self._sample_df()
        periods, _ = _df_to_rows(df)
        assert periods[0] > periods[-1], "Newest period should come first"

    def test_rows_contain_metric_key(self):
        df = self._sample_df()
        _, rows = _df_to_rows(df)
        for row in rows:
            assert "metric" in row

    def test_row_metric_names_match_index(self):
        df = self._sample_df()
        _, rows = _df_to_rows(df)
        metric_names = {r["metric"] for r in rows}
        assert "Total Revenue" in metric_names
        assert "Net Income" in metric_names

    def test_nan_values_become_none(self):
        df = self._sample_df()
        df.iloc[0, 0] = np.nan
        _, rows = _df_to_rows(df)
        none_values = [
            v for row in rows for k, v in row.items() if k != "metric" and v is None
        ]
        assert len(none_values) >= 1

    def test_numeric_values_are_rounded_floats(self):
        df = self._sample_df()
        _, rows = _df_to_rows(df)
        for row in rows:
            for k, v in row.items():
                if k != "metric" and v is not None:
                    assert isinstance(v, float)

    def test_number_of_rows_matches_dataframe_index_length(self):
        df = self._sample_df()
        _, rows = _df_to_rows(df)
        assert len(rows) == len(df.index)

    def test_number_of_periods_matches_dataframe_columns(self):
        df = self._sample_df()
        periods, _ = _df_to_rows(df)
        assert len(periods) == len(df.columns)


# ── place_order validation ────────────────────────────────────────────────────

class TestPlaceOrderValidation:
    """
    Verify place_order returns a rejected OrderResult when neither qty
    nor notional is supplied – without making a real HTTP call.
    """

    def test_no_qty_no_notional_returns_rejected(self):
        from unittest.mock import patch
        import requests

        with patch("requests.post") as mock_post:
            from server import place_order

            result = place_order(
                ticker="AAPL",
                side="buy",
                order_type="market",
                qty=None,
                notional=None,
            )

        assert isinstance(result, OrderResult)
        assert result.status == "rejected"
        mock_post.assert_not_called()  # No HTTP call when validation fails

    def test_rejected_result_has_descriptive_message(self):
        with pytest.raises(Exception):
            pass  # just a placeholder, test below
        from server import place_order

        result = place_order(ticker="TSLA", side="sell", qty=None, notional=None)
        assert "qty" in result.message.lower() or "notional" in result.message.lower()

    def test_network_error_returns_error_status(self):
        from unittest.mock import patch
        from server import place_order

        with patch("requests.post", side_effect=ConnectionError("Network unreachable")):
            result = place_order(ticker="MSFT", side="buy", qty=10)

        assert result.status == "error"
        assert "error" in result.message.lower() or "failed" in result.message.lower()

    def test_alpaca_rejection_returns_rejected_status(self):
        from unittest.mock import MagicMock, patch
        from server import place_order

        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {"message": "insufficient buying power"}

        with patch("requests.post", return_value=mock_resp):
            result = place_order(ticker="AAPL", side="buy", qty=1000)

        assert result.status == "rejected"


# ── VectorStoreInput validation ───────────────────────────────────────────────

class TestVectorStoreInput:
    """Verify VectorStoreInput rejects invalid collection names."""

    def test_invalid_collection_name_raises(self):
        from pydantic import ValidationError
        from server import VectorStoreInput

        with pytest.raises(ValidationError):
            VectorStoreInput(
                collection_name="invalid_collection",  # only 'news' and 'sec_filings' allowed
                query_text="test query",
            )

    def test_valid_news_collection_accepted(self):
        from server import VectorStoreInput
        inp = VectorStoreInput(collection_name="news", query_text="AAPL earnings")
        assert inp.collection_name == "news"

    def test_valid_sec_filings_collection_accepted(self):
        from server import VectorStoreInput
        inp = VectorStoreInput(collection_name="sec_filings", query_text="risk factors")
        assert inp.collection_name == "sec_filings"

    def test_n_results_defaults_to_five(self):
        from server import VectorStoreInput
        inp = VectorStoreInput(collection_name="news", query_text="test")
        assert inp.n_results == 5

    def test_n_results_above_max_raises(self):
        from pydantic import ValidationError
        from server import VectorStoreInput

        with pytest.raises(ValidationError):
            VectorStoreInput(collection_name="news", query_text="test", n_results=51)
