"""
Integration tests for RAG-Ingestion/News/ingestor.py – NewsIngestor.

All external dependencies (Chroma, Yahoo Finance, HTTP scraping, FinBERT)
are mocked. We test the orchestration logic: discover → scrape → chunk →
sentiment → upload, including the skip-if-seen idempotency guard.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_collection():
    """Mock Chroma collection that starts empty (no existing docs)."""
    col = MagicMock()
    col.get.return_value = {"ids": []}  # nothing seen yet
    col.add = MagicMock()
    return col


@pytest.fixture
def mock_chroma_client(mock_collection):
    client = MagicMock()
    client.get_or_create_collection.return_value = mock_collection
    return client


@pytest.fixture
def sample_articles():
    """Two articles: one scrapable (high quality), one not (medium quality)."""
    return [
        {
            "uuid": "uuid-001",
            "title": "Apple Reports Record Revenue",
            "link": "https://example.com/apple-revenue",
            "publisher": "Bloomberg",
            "providerPublishTime": "2025-01-30",
            "summary": "",
            "relatedTickers": ["AAPL"],
        },
        {
            "uuid": "uuid-002",
            "title": "Apple Faces Regulatory Scrutiny",
            "link": "https://paywalled.com/article",
            "publisher": "WSJ",
            "providerPublishTime": "2025-01-29",
            "summary": "Apple faces new antitrust investigation in Europe over App Store practices.",
            "relatedTickers": ["AAPL"],
        },
    ]


@pytest.fixture
def ingestor(mock_chroma_client):
    """
    NewsIngestor with all dependencies replaced by mocks.
    The ChromaClientFactory and embedding function are also patched.
    """
    from News.chunker import NewsChunker
    from News.collector import NewsCollector
    from News.scraper import ArticleScraper
    from News.sentiment import FinBERTSentiment

    mock_collector = MagicMock(spec=NewsCollector)
    mock_scraper = MagicMock(spec=ArticleScraper)
    mock_chunker = MagicMock(spec=NewsChunker)
    mock_sentiment = MagicMock(spec=FinBERTSentiment)

    mock_sentiment.analyse.return_value = {
        "sentiment_label": "positive",
        "sentiment_score": 0.72,
        "sentiment_positive": 0.81,
        "sentiment_negative": 0.09,
        "sentiment_neutral": 0.10,
    }

    with (
        patch("News.ingestor.ChromaClientFactory") as mock_factory_cls,
        patch("News.ingestor.embedding_functions") as mock_ef,
    ):
        mock_factory_cls.create.return_value = mock_chroma_client
        mock_ef.DefaultEmbeddingFunction.return_value = MagicMock()

        from News.ingestor import NewsIngestor

        ing = NewsIngestor(
            collection_name="news",
            collector=mock_collector,
            scraper=mock_scraper,
            chunker=mock_chunker,
            sentiment=mock_sentiment,
            rate_limit_sleep=0,
        )
        ing._collection = mock_chroma_client.get_or_create_collection("news")

    ing._collector = mock_collector
    ing._scraper = mock_scraper
    ing._chunker = mock_chunker
    ing._sentiment = mock_sentiment
    return ing


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestNewsIngestorOrchestration:
    """Verify the full pipeline runs correctly with mocked components."""

    def test_returns_stats_dict_with_required_keys(self, ingestor, sample_articles, mock_collection):
        ingestor._collector.collect.return_value = sample_articles
        ingestor._scraper.scrape.return_value = "Full article text about Apple earnings..."
        ingestor._chunker.chunk.return_value = [
            {"id": "uuid-001-0", "document": "Apple earnings...", "metadata": {"ticker": "AAPL"}}
        ]
        ingestor._collection = mock_collection

        stats = ingestor.ingest("AAPL", "Apple")

        required_keys = {
            "ticker", "total_discovered", "skipped",
            "ingested_high", "ingested_medium", "ingested_low", "total_chunks",
        }
        assert required_keys.issubset(stats.keys())

    def test_ticker_in_stats_matches_input(self, ingestor, mock_collection):
        ingestor._collector.collect.return_value = []
        ingestor._collection = mock_collection
        stats = ingestor.ingest("NVDA", "Nvidia")
        assert stats["ticker"] == "NVDA"

    def test_high_quality_article_when_scrape_succeeds(self, ingestor, sample_articles, mock_collection):
        ingestor._collector.collect.return_value = [sample_articles[0]]
        ingestor._scraper.scrape.return_value = "Full 500+ character article about Apple..."
        ingestor._chunker.chunk.return_value = [
            {"id": "uuid-001-0", "document": "chunk", "metadata": {"ticker": "AAPL"}}
        ]
        ingestor._collection = mock_collection

        stats = ingestor.ingest("AAPL", "Apple")
        assert stats["ingested_high"] == 1
        assert stats["ingested_medium"] == 0

    def test_medium_quality_when_scrape_fails_but_summary_exists(self, ingestor, sample_articles, mock_collection):
        ingestor._collector.collect.return_value = [sample_articles[1]]
        ingestor._scraper.scrape.return_value = ""  # scrape fails
        ingestor._chunker.chunk.return_value = [
            {"id": "uuid-002-0", "document": "summary chunk", "metadata": {"ticker": "AAPL"}}
        ]
        ingestor._collection = mock_collection

        stats = ingestor.ingest("AAPL", "Apple")
        assert stats["ingested_medium"] == 1

    def test_sentiment_called_once_per_article(self, ingestor, sample_articles, mock_collection):
        ingestor._collector.collect.return_value = sample_articles
        ingestor._scraper.scrape.side_effect = ["full text article A...", ""]
        ingestor._chunker.chunk.return_value = [
            {"id": "id-0", "document": "chunk", "metadata": {"ticker": "AAPL"}}
        ]
        ingestor._collection = mock_collection

        ingestor.ingest("AAPL", "Apple")
        assert ingestor._sentiment.analyse.call_count == 2

    def test_sentiment_attached_to_every_chunk_metadata(self, ingestor, sample_articles, mock_collection):
        """Sentiment fields must be present in every chunk's metadata before upload."""
        chunks_added = []

        def mock_add(ids, documents, metadatas):
            chunks_added.extend(metadatas)

        mock_collection.add.side_effect = mock_add
        mock_collection.get.return_value = {"ids": []}
        ingestor._collection = mock_collection

        ingestor._collector.collect.return_value = [sample_articles[0]]
        ingestor._scraper.scrape.return_value = "article text"
        ingestor._chunker.chunk.return_value = [
            {"id": "id-0", "document": "chunk", "metadata": {"ticker": "AAPL"}}
        ]

        ingestor.ingest("AAPL", "Apple")

        for meta in chunks_added:
            assert "sentiment_label" in meta
            assert "sentiment_score" in meta

    def test_chroma_add_called_with_ids_docs_metadatas(self, ingestor, sample_articles, mock_collection):
        mock_collection.get.return_value = {"ids": []}
        ingestor._collection = mock_collection
        ingestor._collector.collect.return_value = [sample_articles[0]]
        ingestor._scraper.scrape.return_value = "article text"
        ingestor._chunker.chunk.return_value = [
            {"id": "id-0", "document": "chunk text", "metadata": {"ticker": "AAPL"}}
        ]

        ingestor.ingest("AAPL", "Apple")
        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args
        assert "ids" in call_kwargs.kwargs
        assert "documents" in call_kwargs.kwargs
        assert "metadatas" in call_kwargs.kwargs


@pytest.mark.integration
class TestNewsIngestorIdempotency:
    """Verify the skip-if-seen guard prevents duplicate ingestion."""

    def test_already_seen_article_is_skipped(self, ingestor, sample_articles, mock_collection):
        mock_collection.get.return_value = {"ids": ["existing-id"]}  # already ingested
        ingestor._collection = mock_collection
        ingestor._collector.collect.return_value = [sample_articles[0]]

        stats = ingestor.ingest("AAPL", "Apple")

        assert stats["skipped"] == 1
        assert stats["ingested_high"] == 0
        mock_collection.add.assert_not_called()

    def test_partial_skip(self, ingestor, sample_articles, mock_collection):
        """First article is new, second is already seen."""
        call_count = 0

        def selective_get(where=None, limit=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"ids": []}          # new article
            return {"ids": ["existing"]}    # already seen

        mock_collection.get.side_effect = selective_get
        ingestor._collection = mock_collection
        ingestor._collector.collect.return_value = sample_articles
        ingestor._scraper.scrape.return_value = "article text"
        ingestor._chunker.chunk.return_value = [
            {"id": "id-0", "document": "chunk", "metadata": {"ticker": "AAPL"}}
        ]

        stats = ingestor.ingest("AAPL", "Apple")
        assert stats["skipped"] == 1
        assert stats["ingested_high"] + stats["ingested_medium"] + stats["ingested_low"] == 1

    def test_empty_article_list_produces_zero_stats(self, ingestor, mock_collection):
        ingestor._collector.collect.return_value = []
        ingestor._collection = mock_collection

        stats = ingestor.ingest("TSLA", "Tesla")
        assert stats["total_discovered"] == 0
        assert stats["total_chunks"] == 0
        mock_collection.add.assert_not_called()
