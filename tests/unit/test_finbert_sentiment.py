"""
Unit tests for RAG-Ingestion/News/sentiment.py – FinBERTSentiment.

We mock torch and transformers to avoid downloading the 400 MB model in CI.
The tests verify business logic: score calculation, label selection, output shape.
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers to build a mocked FinBERTSentiment instance ──────────────────────

def _make_analyzer(probs_matrix: np.ndarray):
    """
    Build a FinBERTSentiment that returns `probs_matrix` from analyse_batch.

    probs_matrix shape: (n_texts, 3) where columns are [positive, negative, neutral].
    """
    with (
        patch("transformers.AutoTokenizer.from_pretrained"),
        patch("transformers.AutoModelForSequenceClassification.from_pretrained"),
    ):
        from News.sentiment import FinBERTSentiment

        analyzer = FinBERTSentiment.__new__(FinBERTSentiment)
        analyzer._model_name = "ProsusAI/finbert"
        analyzer._tokenizer = MagicMock()
        analyzer._model = MagicMock()
        analyzer._model.eval = MagicMock()

        import torch

        analyzer._device = torch.device("cpu")

        mock_tokenizer_output = MagicMock()
        mock_tokenizer_output.to.return_value = mock_tokenizer_output
        analyzer._tokenizer.return_value = mock_tokenizer_output

        mock_logits = MagicMock()
        analyzer._model.return_value = MagicMock(logits=mock_logits)

        mock_softmax_result = MagicMock()
        mock_softmax_result.cpu.return_value.numpy.return_value = probs_matrix

        with patch("torch.nn.functional.softmax", return_value=mock_softmax_result):
            yield analyzer


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestFinBERTOutputShape:
    """Every call must return a dict with exactly the expected keys."""

    REQUIRED_KEYS = {
        "sentiment_label",
        "sentiment_score",
        "sentiment_positive",
        "sentiment_negative",
        "sentiment_neutral",
    }

    def test_analyse_returns_all_required_keys(self):
        probs = np.array([[0.7, 0.2, 0.1]])
        with _make_analyzer(probs) as analyzer:
            with patch("torch.nn.functional.softmax") as mock_sf:
                mock_sf.return_value = MagicMock(
                    cpu=lambda: MagicMock(numpy=lambda: probs)
                )
                result = analyzer.analyse("Strong earnings beat")
        assert self.REQUIRED_KEYS.issubset(set(result.keys()))

    def test_analyse_batch_returns_list_of_dicts(self):
        probs = np.array([[0.7, 0.2, 0.1], [0.1, 0.8, 0.1]])
        with _make_analyzer(probs) as analyzer:
            with patch("torch.nn.functional.softmax") as mock_sf:
                mock_sf.return_value = MagicMock(
                    cpu=lambda: MagicMock(numpy=lambda: probs)
                )
                results = analyzer.analyse_batch(["text one", "text two"])
        assert isinstance(results, list)
        assert len(results) == 2


class TestFinBERTLabelLogic:
    """Label assignment matches argmax of [positive, negative, neutral]."""

    @pytest.mark.parametrize(
        "probs, expected_label",
        [
            (np.array([[0.80, 0.10, 0.10]]), "positive"),
            (np.array([[0.10, 0.75, 0.15]]), "negative"),
            (np.array([[0.15, 0.20, 0.65]]), "neutral"),
            (np.array([[0.34, 0.33, 0.33]]), "positive"),  # tie → argmax = 0 (positive)
        ],
    )
    def test_label_matches_argmax(self, probs, expected_label):
        with _make_analyzer(probs) as analyzer:
            with patch("torch.nn.functional.softmax") as mock_sf:
                mock_sf.return_value = MagicMock(
                    cpu=lambda: MagicMock(numpy=lambda: probs)
                )
                result = analyzer.analyse("test text")
        assert result["sentiment_label"] == expected_label


class TestFinBERTScoreCalculation:
    """Compound score = P(positive) − P(negative), in range [-1, 1]."""

    @pytest.mark.parametrize(
        "pos, neg, neu, expected_score",
        [
            (0.80, 0.10, 0.10, 0.70),   # strongly positive
            (0.10, 0.80, 0.10, -0.70),  # strongly negative
            (0.33, 0.33, 0.34, 0.00),   # neutral
            (1.00, 0.00, 0.00, 1.00),   # pure positive
            (0.00, 1.00, 0.00, -1.00),  # pure negative
        ],
    )
    def test_compound_score_formula(self, pos, neg, neu, expected_score):
        probs = np.array([[pos, neg, neu]])
        with _make_analyzer(probs) as analyzer:
            with patch("torch.nn.functional.softmax") as mock_sf:
                mock_sf.return_value = MagicMock(
                    cpu=lambda: MagicMock(numpy=lambda: probs)
                )
                result = analyzer.analyse("test")
        assert result["sentiment_score"] == pytest.approx(expected_score, abs=0.01)

    def test_score_always_in_valid_range(self):
        """Score must stay within [-1, 1] for any valid probability vector."""
        test_cases = [
            np.array([[0.5, 0.3, 0.2]]),
            np.array([[0.01, 0.98, 0.01]]),
            np.array([[0.98, 0.01, 0.01]]),
        ]
        for probs in test_cases:
            with _make_analyzer(probs) as analyzer:
                with patch("torch.nn.functional.softmax") as mock_sf:
                    mock_sf.return_value = MagicMock(
                        cpu=lambda: MagicMock(numpy=lambda: probs)
                    )
                    result = analyzer.analyse("text")
            assert -1.0 <= result["sentiment_score"] <= 1.0

    def test_individual_probabilities_rounded_to_4_decimals(self):
        probs = np.array([[0.80012, 0.09995, 0.09993]])
        with _make_analyzer(probs) as analyzer:
            with patch("torch.nn.functional.softmax") as mock_sf:
                mock_sf.return_value = MagicMock(
                    cpu=lambda: MagicMock(numpy=lambda: probs)
                )
                result = analyzer.analyse("text")
        assert result["sentiment_positive"] == round(0.80012, 4)
        assert result["sentiment_negative"] == round(0.09995, 4)
        assert result["sentiment_neutral"] == round(0.09993, 4)


class TestFinBERTBatchEquivalence:
    """analyse(text) must return the same result as analyse_batch([text])[0]."""

    def test_single_and_batch_give_same_result(self):
        probs = np.array([[0.60, 0.30, 0.10]])
        with _make_analyzer(probs) as analyzer:
            with patch("torch.nn.functional.softmax") as mock_sf:
                mock_sf.return_value = MagicMock(
                    cpu=lambda: MagicMock(numpy=lambda: probs)
                )
                single = analyzer.analyse("Market outlook positive")
                batch = analyzer.analyse_batch(["Market outlook positive"])
        assert single["sentiment_label"] == batch[0]["sentiment_label"]
        assert single["sentiment_score"] == batch[0]["sentiment_score"]
