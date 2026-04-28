"""
Downloads the most recent 10-K filing for a given ticker from SEC EDGAR
using `sec-edgar-downloader` and stores the raw files as-is under:

    RAG-Ingestion/data/sec-edgar-filings/<TICKER>/10-K/<accession>/

Returns the path to the primary document so the rest of the pipeline
can load it directly without any format conversion.

Folder structure created by sec-edgar-downloader:
    data/
      sec-edgar-filings/
        AAPL/
          10-K/
            0000320193-24-000123/
              primary-document.htm   ← preferred
              full-submission.txt
              ...
"""

from __future__ import annotations

from pathlib import Path

from sec_edgar_downloader import Downloader


_EDGAR_COMPANY = "FinsightAI"
_EDGAR_EMAIL   = "admin@finsightai.com"

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Preference order when looking for the primary filing document
_DOC_CANDIDATES = ["primary-document.htm", "*.htm", "*.html"]


class TenKDownloader:
    """
    Downloads the latest 10-K filing for a ticker via sec-edgar-downloader
    and returns the path to the primary document file.
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, ticker: str) -> Path | None:
        """
        Ensure the latest 10-K for *ticker* is present on disk and return
        the path to its primary document.

        If the filing directory already exists, the SEC download is skipped
        and the cached primary document is returned directly.

        Args:
            ticker: Stock ticker symbol (e.g. 'AAPL').

        Returns:
            Path to the primary filing document, or None if unavailable.
        """
        filing_dir = self._data_dir / "sec-edgar-filings" / ticker / "10-K"

        if filing_dir.exists() and any(filing_dir.iterdir()):
            print(f"[TenKDownloader] {ticker}: already downloaded at {filing_dir}")
            return self._find_primary_document(filing_dir, ticker)

        print(f"[TenKDownloader] {ticker}: fetching from SEC EDGAR...")
        try:
            dl = Downloader(_EDGAR_COMPANY, _EDGAR_EMAIL, self._data_dir)
            dl.get("10-K", ticker, limit=1, download_details=True)
        except Exception as exc:
            print(f"[TenKDownloader] {ticker}: download error — {exc}")
            return None

        if not filing_dir.exists() or not any(filing_dir.iterdir()):
            print(f"[TenKDownloader] {ticker}: no filing directory created after download.")
            return None

        doc = self._find_primary_document(filing_dir, ticker)
        if doc:
            print(f"[TenKDownloader] {ticker}: ready → {doc}")
        else:
            print(f"[TenKDownloader] {ticker}: no usable document found in {filing_dir}")
        return doc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_primary_document(self, filing_dir: Path, ticker: str) -> Path | None:
        """
        Search accession sub-directories for the best document to parse.

        Priority:
          1. primary-document.htm  (sec-edgar-downloader canonical name)
          2. Any other .htm file   (company-named HTM, e.g. aapl-20240928.htm)
          3. Any .html file
        """
        for accession_dir in sorted(filing_dir.iterdir()):
            if not accession_dir.is_dir():
                continue

            for pattern in _DOC_CANDIDATES:
                matches = sorted(accession_dir.glob(pattern))
                if matches:
                    return matches[0]

        return None
