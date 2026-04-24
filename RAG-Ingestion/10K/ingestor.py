from shared.base_ingestor import BaseIngestor
from tenk.loader import HTMLLoader
from tenk.parser import TenKParser
from tenk.chunker import TenKChunker
from tenk.embedder import TenKEmbedder


class TenKIngestor(BaseIngestor):
    """
    Orchestrates the full 10-K ingestion pipeline:
      HTML file → parse sections → chunk → embed & upload to Chroma.
    """

    def __init__(
        self,
        loader: HTMLLoader | None = None,
        parser: TenKParser | None = None,
        chunker: TenKChunker | None = None,
        embedder: TenKEmbedder | None = None,
    ) -> None:
        self._loader = loader or HTMLLoader()
        self._parser = parser or TenKParser()
        self._chunker = chunker or TenKChunker()
        self._embedder = embedder or TenKEmbedder()

    def ingest(self, file_path: str, company: str) -> dict:
        """
        Run the complete ingestion pipeline for one 10-K filing.

        Args:
            file_path: Path to the 10-K HTML file on disk.
            company:   Company name used for metadata and logging.

        Returns:
            Stats dict with keys: company, file_path, sections_found,
            total_chunks, chunks_per_section.
        """
        print(f"\n[TenKIngestor] Starting ingestion for {company} ({file_path})")

        html = self._loader.load(file_path)

        sections = self._parser.parse(company, html)
        sections_found = [k for k, v in sections.items() if v.strip()]
        print(f"[TenKIngestor] Sections extracted: {sections_found}")

        documents = self._chunker.chunk(sections, company)
        print(f"[TenKIngestor] Total chunks created: {len(documents)}")

        chunks_per_section: dict[str, int] = {}
        for doc in documents:
            section = doc.metadata.get("section", "unknown")
            chunks_per_section[section] = chunks_per_section.get(section, 0) + 1

        self._embedder.upload(documents)

        stats = {
            "company": company,
            "file_path": file_path,
            "sections_found": sections_found,
            "total_chunks": len(documents),
            "chunks_per_section": chunks_per_section,
        }

        print(f"[TenKIngestor] Done. Stats: {stats}")
        return stats
