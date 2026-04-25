"""
FinBERT sentiment analyser.

Model: ProsusAI/finbert
Labels (index order from model config):
  0 → positive
  1 → negative
  2 → neutral

Compound score = P(positive) − P(negative)  ∈ [-1, 1]
  +1.0 → purely bullish
  -1.0 → purely bearish
   0.0 → neutral / conflicted

The model is loaded lazily on first call so importing this module does not
trigger a download if FinBERT is never used.
"""

from __future__ import annotations

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from shared import config as cfg

# FinBERT label index → name (matches ProsusAI/finbert config)
_LABEL_NAMES = {0: "positive", 1: "negative", 2: "neutral"}


class FinBERTSentiment:
    """
    Wraps ProsusAI/finbert for batch and single-text sentiment inference.

    The model and tokenizer are loaded once and reused across all calls.
    GPU is used automatically when available.
    """

    def __init__(self, model_name: str = cfg.DEFAULT_FINBERT_MODEL) -> None:
        self._model_name = model_name
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[FinBERTSentiment] Loading {model_name} on {self._device}...")
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._model.to(self._device)
        self._model.eval()
        print("[FinBERTSentiment] Model ready.")

    def analyse(self, text: str) -> dict:
        """
        Run FinBERT on a single text and return sentiment metadata fields.

        Args:
            text: Raw text to classify (will be truncated to 512 tokens).

        Returns:
            Dict with keys:
              sentiment_label    – "positive" | "negative" | "neutral"
              sentiment_score    – compound float in [-1, 1]
              sentiment_positive – probability for positive class
              sentiment_negative – probability for negative class
              sentiment_neutral  – probability for neutral class
        """
        return self.analyse_batch([text])[0]

    def analyse_batch(self, texts: list[str]) -> list[dict]:
        """
        Run FinBERT on a batch of texts.

        Args:
            texts: List of raw text strings.

        Returns:
            List of sentiment dicts (same shape as `analyse`), one per input text.
        """
        inputs = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=cfg.FINBERT_MAX_LENGTH,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            logits = self._model(**inputs).logits

        probs = torch.nn.functional.softmax(logits, dim=-1).cpu().numpy()

        results = []
        for prob in probs:
            pos, neg, neu = float(prob[0]), float(prob[1]), float(prob[2])
            label_idx = int(prob.argmax())
            results.append(
                {
                    "sentiment_label":    _LABEL_NAMES[label_idx],
                    "sentiment_score":    round(pos - neg, 4),
                    "sentiment_positive": round(pos, 4),
                    "sentiment_negative": round(neg, 4),
                    "sentiment_neutral":  round(neu, 4),
                }
            )
        return results
