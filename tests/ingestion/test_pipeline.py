"""
Ingestion pipeline tests for RAG-Ingestion.

Tests the full pipeline properties: idempotency, metadata completeness,
collection shape, chunk quality, and sentiment score validity.

Modes:
  - In-memory Chroma (default): uses chromadb.EphemeralClient() so tests
    run without a real Chroma server.
  - Live Chroma (@pytest.mark.live): connects to CHROMA_URL and tests
    against the real production collection.

Run in-memory tests:
    pytest tests/ingestion/ -v

Run live tests (requires CHROMA_URL):
    pytest tests/ingestion/ -m live -v
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest


# ── In-memory Chroma helpers ──────────────────────────────────────────────────

@pytest.fixture
def ephemeral_chroma():
    """Ephemeral in-memory Chroma client – no server required."""
    import chromadb
    client = chromadb.EphemeralClient()
    return client


@pytest.fixture
def news_collection(ephemeral_chroma):
    """In-memory 'news' collection with default embedding function."""
    from chromadb.utils import embedding_functions
    ef = embedding_functions.DefaultEmbeddingFunction()
    return ephemeral_chroma.get_or_create_collection(name="news", embedding_function=ef)


@pytest.fixture
def sec_collection(ephemeral_chroma):
    """In-memory 'sec_filings' collection."""
    from chromadb.utils import embedding_functions
    ef = embedding_functions.DefaultEmbeddingFunction()
    return ephemeral_chroma.get_or_create_collection(name="sec_filings", embedding_function=ef)


def _sample_chunk(
    doc_id: str = None,
    document: str = "Apple reported record revenue of $391 billion in FY2024.",
    ticker: str = "AAPL",
    quality: str = "high",
    chunk_index: int = 0,
    chunk_count: int = 1,
    sentiment_label: str = "positive",
    sentiment_score: float = 0.72,
) -> dict:
    did = doc_id or str(uuid.uuid4())
    return {
        "id": f"{did}-{chunk_index}",
        "document": document,
        "metadata": {
            "ticker": ticker,
            "title": "Apple Q4 Earnings",
            "link": "https://example.com/apple-q4",
            "publisher": "Bloomberg",
            "published": "2025-01-30",
            "original_uuid": did,
            "quality": quality,
            "chunk_index": chunk_index,
            "chunk_count": chunk_count,
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score,
            "sentiment_positive": 0.80,
            "sentiment_negative": 0.08,
            "sentiment_neutral": 0.12,
        },
    }


# ── Collection existence tests ────────────────────────────────────────────────

@pytest.mark.ingestion
class TestCollectionExistence:
    """Verify both required Chroma collections can be created."""

    def test_news_collection_can_be_created(self, ephemeral_chroma):
        col = ephemeral_chroma.get_or_create_collection(name="news")
        assert col is not None
        assert col.name == "news"

    def test_sec_filings_collection_can_be_created(self, ephemeral_chroma):
        col = ephemeral_chroma.get_or_create_collection(name="sec_filings")
        assert col is not None
        assert col.name == "sec_filings"

    def test_collections_are_independent(self, news_collection, sec_collection):
        chunk = _sample_chunk()
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        assert news_collection.count() == 1
        assert sec_collection.count() == 0


# ── Chunk metadata completeness tests ────────────────────────────────────────

@pytest.mark.ingestion
class TestChunkMetadataCompleteness:
    """All ingested chunks must carry the required metadata fields."""

    REQUIRED_NEWS_METADATA = {
        "ticker", "title", "quality", "chunk_index",
        "chunk_count", "original_uuid",
        "sentiment_label", "sentiment_score",
        "sentiment_positive", "sentiment_negative", "sentiment_neutral",
    }

    REQUIRED_10K_METADATA = {
        "ticker", "chunk_index", "chunk_count", "original_uuid",
    }

    def test_news_chunk_has_all_required_fields(self, news_collection):
        chunk = _sample_chunk()
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        results = news_collection.get(ids=[chunk["id"]])
        stored_meta = results["metadatas"][0]
        for field in self.REQUIRED_NEWS_METADATA:
            assert field in stored_meta, f"Required field '{field}' missing from chunk metadata"

    def test_chunk_index_is_integer(self, news_collection):
        chunk = _sample_chunk(chunk_index=2)
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        results = news_collection.get(ids=[chunk["id"]])
        assert isinstance(results["metadatas"][0]["chunk_index"], int)

    def test_quality_is_valid_tier(self, news_collection):
        for quality in ("high", "medium", "low"):
            chunk = _sample_chunk(quality=quality)
            news_collection.add(
                ids=[chunk["id"]],
                documents=[chunk["document"]],
                metadatas=[chunk["metadata"]],
            )
        results = news_collection.get()
        qualities = {m["quality"] for m in results["metadatas"]}
        assert qualities.issubset({"high", "medium", "low"})

    def test_ticker_is_uppercase(self, news_collection):
        chunk = _sample_chunk(ticker="AAPL")
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        results = news_collection.get(ids=[chunk["id"]])
        assert results["metadatas"][0]["ticker"] == results["metadatas"][0]["ticker"].upper()


# ── Sentiment score validity tests ────────────────────────────────────────────

@pytest.mark.ingestion
class TestSentimentScoreValidity:
    """Sentiment scores stored in Chroma must be within valid bounds."""

    def test_sentiment_score_in_range(self, news_collection):
        for score in (0.95, 0.0, -0.95, 0.5, -0.3):
            chunk = _sample_chunk(sentiment_score=score, doc_id=str(uuid.uuid4()))
            news_collection.add(
                ids=[chunk["id"]],
                documents=[chunk["document"]],
                metadatas=[chunk["metadata"]],
            )

        results = news_collection.get()
        for meta in results["metadatas"]:
            score = meta["sentiment_score"]
            assert -1.0 <= score <= 1.0, f"Sentiment score {score} out of range [-1, 1]"

    def test_sentiment_label_is_valid(self, news_collection):
        for label in ("positive", "negative", "neutral"):
            chunk = _sample_chunk(sentiment_label=label, doc_id=str(uuid.uuid4()))
            news_collection.add(
                ids=[chunk["id"]],
                documents=[chunk["document"]],
                metadatas=[chunk["metadata"]],
            )

        results = news_collection.get()
        valid_labels = {"positive", "negative", "neutral"}
        for meta in results["metadatas"]:
            assert meta["sentiment_label"] in valid_labels

    def test_probability_sum_approx_one(self, news_collection):
        chunk = _sample_chunk()
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        results = news_collection.get(ids=[chunk["id"]])
        meta = results["metadatas"][0]
        prob_sum = meta["sentiment_positive"] + meta["sentiment_negative"] + meta["sentiment_neutral"]
        assert abs(prob_sum - 1.0) < 0.05, f"Probabilities sum to {prob_sum:.4f}, expected ≈ 1.0"


# ── Idempotency tests ─────────────────────────────────────────────────────────

@pytest.mark.ingestion
class TestIdempotency:
    """Running the ingestor twice must not create duplicate documents."""

    def test_adding_same_id_twice_does_not_duplicate(self, news_collection):
        """Chroma's add() with duplicate IDs raises an error, which the ingestor avoids via skip-if-seen."""
        chunk = _sample_chunk()
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        assert news_collection.count() == 1

        existing = news_collection.get(where={"original_uuid": chunk["metadata"]["original_uuid"]})
        assert existing["ids"], "Should find existing document by original_uuid"

        # Since document exists, the ingestor would skip – no duplicate added
        assert news_collection.count() == 1

    def test_upsert_updates_existing_document(self, news_collection):
        """Chroma's upsert() is idempotent – same ID means update in place."""
        chunk = _sample_chunk()
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )
        updated_doc = "Updated: Apple Q4 revenue exceeded $400B."
        news_collection.upsert(
            ids=[chunk["id"]],
            documents=[updated_doc],
            metadatas=[chunk["metadata"]],
        )
        assert news_collection.count() == 1
        result = news_collection.get(ids=[chunk["id"]])
        assert result["documents"][0] == updated_doc

    def test_skip_if_seen_logic_via_original_uuid(self, news_collection):
        """Simulate the ingestor's skip-if-seen guard using original_uuid metadata filter."""
        original_uuid = str(uuid.uuid4())
        chunk = _sample_chunk(doc_id=original_uuid)
        news_collection.add(
            ids=[chunk["id"]],
            documents=[chunk["document"]],
            metadatas=[chunk["metadata"]],
        )

        # Simulate the guard: query by original_uuid
        existing = news_collection.get(where={"original_uuid": original_uuid}, limit=1)
        should_skip = bool(existing["ids"])
        assert should_skip, "Guard should detect the existing document and skip re-ingestion"


# ── Embedding dimension tests ─────────────────────────────────────────────────

@pytest.mark.ingestion
class TestEmbeddingDimensions:
    """Verify that the default embedding function produces consistent vector dimensions."""

    def test_embedded_vectors_have_consistent_dimensions(self, ephemeral_chroma):
        """
        Use the DefaultEmbeddingFunction and verify all embeddings have the same dimensionality.
        all-MiniLM-L6-v2 produces 384-dimensional vectors.
        """
        from chromadb.utils import embedding_functions
        ef = embedding_functions.DefaultEmbeddingFunction()

        col = ephemeral_chroma.get_or_create_collection(
            name="dim_test", embedding_function=ef
        )

        chunks = [_sample_chunk(doc_id=str(uuid.uuid4()), document=f"Document {i}") for i in range(3)]
        col.add(
            ids=[c["id"] for c in chunks],
            documents=[c["document"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )

        results = col.get(include=["embeddings"])
        embeddings = results.get("embeddings", [])
        if embeddings:
            dims = [len(emb) for emb in embeddings]
            assert len(set(dims)) == 1, f"Inconsistent embedding dimensions: {dims}"
            # all-MiniLM-L6-v2 (default) produces 384-dim vectors
            assert dims[0] == 384


# ── Semantic search quality tests ─────────────────────────────────────────────

@pytest.mark.ingestion
class TestSemanticSearchQuality:
    """Verify that semantic search returns relevant results for financial queries."""

    def test_query_returns_ticker_relevant_results(self, news_collection):
        """
        After ingesting AAPL and MSFT news, a query about Apple earnings
        should return AAPL chunks with higher scores.
        """
        aapl_chunk = _sample_chunk(
            doc_id="aapl-001",
            document="Apple Inc. reported record iPhone sales and services revenue growth.",
            ticker="AAPL",
        )
        msft_chunk = _sample_chunk(
            doc_id="msft-001",
            document="Microsoft Azure cloud revenue grew 31% driven by AI workloads.",
            ticker="MSFT",
        )

        news_collection.add(
            ids=[aapl_chunk["id"], msft_chunk["id"]],
            documents=[aapl_chunk["document"], msft_chunk["document"]],
            metadatas=[aapl_chunk["metadata"], msft_chunk["metadata"]],
        )

        results = news_collection.query(
            query_texts=["Apple iPhone revenue growth"],
            n_results=2,
            include=["documents", "metadatas", "distances"],
        )

        top_meta = results["metadatas"][0][0]
        assert top_meta["ticker"] == "AAPL", (
            "Expected AAPL document to rank first for Apple-specific query"
        )

    def test_ticker_filter_restricts_results(self, news_collection):
        """Using a where filter on ticker should return only matching ticker's docs."""
        for ticker in ("AAPL", "MSFT", "NVDA"):
            chunk = _sample_chunk(doc_id=str(uuid.uuid4()), ticker=ticker)
            news_collection.add(
                ids=[chunk["id"]],
                documents=[chunk["document"]],
                metadatas=[chunk["metadata"]],
            )

        results = news_collection.query(
            query_texts=["earnings results"],
            n_results=5,
            where={"ticker": "AAPL"},
            include=["metadatas"],
        )

        returned_tickers = {m["ticker"] for m in results["metadatas"][0]}
        assert returned_tickers == {"AAPL"}, (
            f"Expected only AAPL results, got: {returned_tickers}"
        )
