import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from shared import config as cfg


class NewsChunker:
    """
    Splits news article text into overlapping chunks using
    RecursiveCharacterTextSplitter.

    News-specific defaults (500 / 100) are intentionally smaller than the
    10-K defaults (1000 / 200): news articles are shorter and more
    conversational, so tighter chunks keep each piece focused on a single
    idea and avoid one long article becoming a single wall-of-text chunk.
    """

    def __init__(
        self,
        chunk_size: int = cfg.DEFAULT_NEWS_CHUNK_SIZE,
        chunk_overlap: int = cfg.DEFAULT_NEWS_CHUNK_OVERLAP,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text: str, metadata: dict, quality: str) -> list[dict]:
        """
        Split article text into character-based chunks with Chroma-ready metadata.

        Args:
            text:     Article body text (or synthetic headline document).
            metadata: Base metadata dict from the news item (ticker, title, etc.).
            quality:  Tier label — 'high' (full article), 'medium' (summary),
                      or 'low' (synthetic headline).

        Returns:
            List of dicts, each containing 'id', 'document', and 'metadata',
            ready to be passed directly to chromadb Collection.add().
        """
        raw_chunks = self._splitter.split_text(text) if text.strip() else []

        if not raw_chunks:
            raw_chunks = [metadata.get("title", text)]

        original_uuid = metadata.get("original_uuid", str(uuid.uuid4()))
        # Include ticker in the chunk ID so the same article stored for
        # multiple tickers gets distinct IDs in the collection.
        ticker = metadata.get("ticker", "unknown")

        result: list[dict] = []
        for idx, chunk in enumerate(raw_chunks):
            chunk_metadata = {
                **metadata,
                "quality": quality,
                "chunk_index": idx,
                "chunk_count": len(raw_chunks),
                "original_uuid": original_uuid,
            }
            result.append(
                {
                    "id": f"{ticker}-{original_uuid}-{idx}",
                    "document": chunk,
                    "metadata": chunk_metadata,
                }
            )

        return result
