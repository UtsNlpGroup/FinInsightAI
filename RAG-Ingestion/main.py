"""
RAG-Ingestion entry point.

Usage (run from the finsightAI project root):
    python RAG-Ingestion/main.py --mode 10k
    python RAG-Ingestion/main.py --mode news
    python RAG-Ingestion/main.py --mode all

Companies are read dynamically from the Supabase `public.companies` table so
that this script never needs to be edited when tickers change.  For 10-K runs,
filings are downloaded from SEC EDGAR via edgartools and cached as HTML files
under RAG-Ingestion/data/ before being parsed and embedded.

The folder is named 'RAG-Ingestion' (hyphen) and one sub-package is named '10K'
(digit prefix) — both are invalid Python package names.  This bootstrap block
adds the RAG-Ingestion directory to sys.path and registers the '10K' folder
under the importable alias 'tenk', so all sub-modules can be imported normally.
"""

import importlib.util
import sys
from pathlib import Path

# ── Bootstrap ──────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent

# Allow plain absolute imports from inside RAG-Ingestion/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Register RAG-Ingestion/10K/ as the Python package 'tenk'
_tenk_path = _HERE / "10K"
_tenk_spec = importlib.util.spec_from_file_location(
    "tenk",
    _tenk_path / "__init__.py",
    submodule_search_locations=[str(_tenk_path)],
)
_tenk_pkg = importlib.util.module_from_spec(_tenk_spec)
sys.modules["tenk"] = _tenk_pkg
_tenk_spec.loader.exec_module(_tenk_pkg)
# ───────────────────────────────────────────────────────────────────────────

import argparse

from tenk.downloader import TenKDownloader
from tenk.ingestor import TenKIngestor
from News.ingestor import NewsIngestor
from shared.supabase_client import fetch_companies, Company


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_companies() -> list[Company]:
    """Fetch tracked companies from Supabase public.companies."""
    print("Fetching company list from Supabase...")
    companies = fetch_companies()
    if not companies:
        print("  No companies found in Supabase. Nothing to ingest — exiting.")
        sys.exit(0)
    print(f"  Found {len(companies)} companies: {[c.ticker for c in companies]}")
    return companies


# ---------------------------------------------------------------------------
# Pipeline runners
# ---------------------------------------------------------------------------


def run_10k_ingestion(companies: list[Company]) -> None:
    print("\n" + "=" * 60)
    print("  10-K Ingestion Pipeline")
    print("=" * 60)

    downloader = TenKDownloader()
    ingestor   = TenKIngestor()
    all_stats: list[dict] = []

    for company in companies:
        file_path = downloader.download(company.ticker)

        if file_path is None:
            print(f"[WARN] No 10-K found for {company.ticker}, skipping.")
            continue

        stats = ingestor.ingest(str(file_path), company.company_name, ticker=company.ticker)
        stats["ticker"] = company.ticker
        all_stats.append(stats)

    print("\n--- 10-K Ingestion Summary ---")
    for s in all_stats:
        print(f"  {s['ticker']} ({s['company']}): {s['total_chunks']} chunks")


def run_news_ingestion(companies: list[Company]) -> None:
    print("\n" + "=" * 60)
    print("  News Ingestion Pipeline")
    print("=" * 60)

    ingestor = NewsIngestor()
    all_stats: list[dict] = []

    for company in companies:
        stats = ingestor.ingest(company.ticker, company.company_name)
        all_stats.append(stats)

    print("\n--- News Ingestion Summary ---")
    for s in all_stats:
        print(
            f"  {s['ticker']}: discovered={s['total_discovered']}, "
            f"high={s['ingested_high']}, medium={s['ingested_medium']}, "
            f"low={s['ingested_low']}, chunks={s['total_chunks']}, "
            f"skipped={s['skipped']}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="RAG Ingestion: load 10-K filings and/or news articles into Chroma."
    )
    p.add_argument(
        "--mode",
        choices=["10k", "news", "all"],
        default="all",
        help="Which pipeline to run (default: all).",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()

    companies = load_companies()

    if args.mode in ("10k", "all"):
        run_10k_ingestion(companies)

    if args.mode in ("news", "all"):
        run_news_ingestion(companies)

    print("\nIngestion complete.")


if __name__ == "__main__":
    main()
