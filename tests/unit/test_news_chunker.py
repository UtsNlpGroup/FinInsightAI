"""
Unit tests for RAG-Ingestion/News/chunker.py – NewsChunker.

These tests run entirely in-process with no external I/O.
The RecursiveCharacterTextSplitter is real (it's deterministic), but Chroma
and Supabase are never touched.
"""

import pytest

from News.chunker import NewsChunker


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def chunker() -> NewsChunker:
    """Chunker with a small chunk_size so tests don't need huge inputs."""
    return NewsChunker(chunk_size=200, chunk_overlap=20)


@pytest.fixture
def short_text() -> str:
    return "Apple reported record quarterly revenue of $120 billion."


@pytest.fixture
def long_text() -> str:
    # ~600 characters → should produce >= 2 chunks with chunk_size=200
    return (
        "Apple Inc. reported record quarterly revenue in its latest earnings release. "
        "The company's services segment grew 24% year-over-year, driven by the App Store, "
        "Apple TV+, and iCloud subscriptions. CEO Tim Cook expressed confidence in AI integration. "
        "iPhone unit sales exceeded analyst expectations by a significant margin this quarter. "
        "The board approved a $110 billion share buyback programme, the largest in the company's history. "
        "Analysts revised their price targets upward following the strong results."
    )


@pytest.fixture
def base_metadata() -> dict:
    return {
        "ticker": "AAPL",
        "title": "Apple Reports Record Revenue",
        "link": "https://example.com/aapl-earnings",
        "publisher": "Bloomberg",
        "published": "2025-01-30",
        "original_uuid": "aaaa-bbbb-cccc-dddd",
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestNewsChunkerBasicOutput:
    """Verify output structure is always Chroma-ready."""

    def test_returns_list(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="high")
        assert isinstance(result, list)

    def test_each_item_has_required_keys(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="high")
        for item in result:
            assert "id" in item, "Each chunk must have an 'id'"
            assert "document" in item, "Each chunk must have a 'document'"
            assert "metadata" in item, "Each chunk must have a 'metadata'"

    def test_chunk_ids_are_unique(self, chunker, long_text, base_metadata):
        result = chunker.chunk(long_text, base_metadata, quality="high")
        ids = [item["id"] for item in result]
        assert len(ids) == len(set(ids)), "All chunk IDs must be unique"

    def test_id_format_uses_uuid_and_index(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="medium")
        assert result[0]["id"].startswith("aaaa-bbbb-cccc-dddd-")

    def test_documents_are_non_empty_strings(self, chunker, long_text, base_metadata):
        result = chunker.chunk(long_text, base_metadata, quality="high")
        for item in result:
            assert isinstance(item["document"], str)
            assert len(item["document"]) > 0


class TestNewsChunkerMetadata:
    """Verify metadata is correctly attached to every chunk."""

    def test_quality_propagated_to_all_chunks(self, chunker, long_text, base_metadata):
        for quality in ("high", "medium", "low"):
            result = chunker.chunk(long_text, base_metadata, quality=quality)
            for item in result:
                assert item["metadata"]["quality"] == quality

    def test_ticker_propagated(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="high")
        for item in result:
            assert item["metadata"]["ticker"] == "AAPL"

    def test_chunk_index_is_sequential(self, chunker, long_text, base_metadata):
        result = chunker.chunk(long_text, base_metadata, quality="high")
        indices = [item["metadata"]["chunk_index"] for item in result]
        assert indices == list(range(len(result)))

    def test_chunk_count_consistent_across_chunks(self, chunker, long_text, base_metadata):
        result = chunker.chunk(long_text, base_metadata, quality="high")
        expected_count = len(result)
        for item in result:
            assert item["metadata"]["chunk_count"] == expected_count

    def test_original_uuid_preserved(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="high")
        for item in result:
            assert item["metadata"]["original_uuid"] == "aaaa-bbbb-cccc-dddd"

    def test_base_metadata_keys_present(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="high")
        for item in result:
            for key in ("ticker", "title", "link", "publisher", "published"):
                assert key in item["metadata"]


class TestNewsChunkerEdgeCases:
    """Edge cases: empty input, whitespace, very short text."""

    def test_empty_string_uses_title_as_fallback(self, chunker, base_metadata):
        result = chunker.chunk("", base_metadata, quality="low")
        assert len(result) == 1
        assert result[0]["document"] == base_metadata["title"]

    def test_whitespace_only_uses_title_as_fallback(self, chunker, base_metadata):
        result = chunker.chunk("   \n  \t  ", base_metadata, quality="low")
        assert len(result) == 1

    def test_text_shorter_than_chunk_size_produces_one_chunk(self, chunker, short_text, base_metadata):
        result = chunker.chunk(short_text, base_metadata, quality="medium")
        assert len(result) == 1

    def test_long_text_produces_multiple_chunks(self, chunker, long_text, base_metadata):
        result = chunker.chunk(long_text, base_metadata, quality="high")
        assert len(result) >= 2

    def test_auto_generates_uuid_when_not_in_metadata(self, chunker, short_text):
        metadata_no_uuid = {"ticker": "MSFT", "title": "Test"}
        result = chunker.chunk(short_text, metadata_no_uuid, quality="low")
        assert len(result[0]["id"]) > 5  # UUID was generated

    def test_metadata_without_title_does_not_crash(self, chunker):
        result = chunker.chunk("", {"ticker": "TSLA"}, quality="low")
        assert len(result) >= 1


class TestNewsChunkerChunkSizes:
    """Verify chunk sizes respect the configured maximum."""

    def test_chunks_respect_max_size(self):
        max_size = 100
        chunker = NewsChunker(chunk_size=max_size, chunk_overlap=10)
        long_text = "word " * 200  # 1000 characters
        base_metadata = {"ticker": "AAPL", "title": "test", "original_uuid": "u1"}
        result = chunker.chunk(long_text, base_metadata, quality="high")
        for item in result:
            assert len(item["document"]) <= max_size + 50  # splitter allows small overshoot
