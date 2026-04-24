"""
Downloads the most recent 10-K filing for a given ticker from SEC EDGAR
using `edgartools` (already a project dependency) and saves the primary
document as an HTML file under:

    RAG-Ingestion/data/<TICKER>_10K.html

Returns the saved file path so the rest of the pipeline can load it.
"""

from __future__ import annotations

from pathlib import Path

import edgar


# SEC requires a user-agent string: "Company Name email@example.com"
_EDGAR_IDENTITY = "FinsightAI admin@finsightai.com"

# Where to write the downloaded HTML files
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class TenKDownloader:
    """
    Downloads the latest 10-K filing for a ticker and writes it to disk as HTML.
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        edgar.set_identity(_EDGAR_IDENTITY)

    def download(self, ticker: str) -> Path | None:
        """
        Fetch the most recent 10-K for *ticker* and save it to the data directory.

        Args:
            ticker: Stock ticker symbol (e.g. 'AAPL').

        Returns:
            Path to the saved HTML file, or None if no filing was found.
        """
        out_path = self._data_dir / f"{ticker}_10K.html"

        if out_path.exists():
            print(f"[TenKDownloader] {ticker}: cached at {out_path}")
            return out_path

        print(f"[TenKDownloader] {ticker}: fetching from SEC EDGAR...")
        try:
            company = edgar.Company(ticker)
            filings = company.get_filings(form="10-K")

            if not filings:
                print(f"[TenKDownloader] {ticker}: no 10-K filings found.")
                return None

            filing = filings.latest()
            html_content = self._extract_html(filing)

            if not html_content:
                print(f"[TenKDownloader] {ticker}: could not extract HTML from filing.")
                return None

            out_path.write_text(html_content, encoding="utf-8")
            print(f"[TenKDownloader] {ticker}: saved {len(html_content):,} chars → {out_path}")
            return out_path

        except Exception as exc:
            print(f"[TenKDownloader] {ticker}: error — {exc}")
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_html(filing) -> str | None:
        """
        Try multiple edgartools API surfaces to get the HTML of the primary
        10-K document, falling back to plain text wrapped in <pre> tags.
        """
        # Try the primary document first
        try:
            doc = filing.primary_document
            if doc is not None:
                html = doc.html()
                if html:
                    return html
        except Exception:
            pass

        # Try .document attribute (older edgartools versions)
        try:
            doc = filing.document
            if doc is not None:
                html = doc.html()
                if html:
                    return html
        except Exception:
            pass

        # Fallback: plain text wrapped in <pre> so the HTML loader still works
        try:
            text = filing.text()
            if text:
                return f"<html><body><pre>{text}</pre></body></html>"
        except Exception:
            pass

        return None
