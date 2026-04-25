from shared.base_ingestor import BaseIngestor
from tenk.loader import HTMLLoader
from tenk.parser import TenKParser
from tenk.chunker import TenKChunker
from tenk.embedder import TenKEmbedder


class TenKIngestor(BaseIngestor):
    """
    Orchestrates the 10-K ingestion pipeline:
      File on disk → plain text → chunks → upload to Chroma.
    """

    def __init__(
        self,
        loader: HTMLLoader | None = None,
        parser: TenKParser | None = None,
        chunker: TenKChunker | None = None,
        embedder: TenKEmbedder | None = None,
    ) -> None:
        self._loader  = loader  or HTMLLoader()
        self._parser  = parser  or TenKParser()
        self._chunker = chunker or TenKChunker()
        self._embedder = embedder or TenKEmbedder()

    def ingest(self, file_path: str, company: str, ticker: str = "") -> dict:
        """
        Run the full ingestion pipeline for one 10-K filing.

        Args:
            file_path: Path to the filing document on disk.
            company:   Company name used for metadata and logging.
            ticker:    Stock ticker symbol stored in chunk metadata.

        Returns:
            Stats dict with keys: company, file_path, total_chunks.
        """
        print(f"\n[TenKIngestor] Starting ingestion for {company} ({ticker}) from {file_path}")

        raw = self._loader.load(file_path)
        text = self._parser.parse(company, raw)

        documents = self._chunker.chunk(text, company, ticker=ticker)
        print(f"[TenKIngestor] Total chunks: {len(documents)}")

        self._embedder.upload(documents)

        stats = {
            "company": company,
            "file_path": file_path,
            "total_chunks": len(documents),
            # kept for backwards-compat with summary print in main.py
            "chunks_per_section": {},
        }

        print(f"[TenKIngestor] Done. {len(documents)} chunks for {company}.")
        return stats
