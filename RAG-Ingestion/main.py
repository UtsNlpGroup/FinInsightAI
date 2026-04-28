"""
RAG-Ingestion entry point.

Usage (run from the finsightAI project root):
    python RAG-Ingestion/main.py --mode 10k
    python RAG-Ingestion/main.py --mode news
    python RAG-Ingestion/main.py --mode all

Add --verbose / -v for step-by-step debug output.

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
import logging
import sys
import time
from pathlib import Path

# ── Bootstrap ──────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_tenk_path = _HERE / "10K"
_tenk_spec = importlib.util.spec_from_file_location(
    "tenk",
    _tenk_path / "__init__.py",
    submodule_search_locations=[str(_tenk_path)],
)
_tenk_pkg = importlib.util.module_from_spec(_tenk_spec)
sys.modules["tenk"] = _tenk_pkg
_tenk_spec.loader.exec_module(_tenk_pkg)
# ───────────────────────────────────────────────────────────────────────────────

import argparse

log = logging.getLogger("rag_ingestion")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Surface debug logs from third-party libraries only in verbose mode
    for noisy in ("urllib3", "httpx", "httpcore", "huggingface_hub", "filelock"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if verbose else logging.WARNING)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(msg: str) -> None:
    """Print a clearly-visible pipeline step banner."""
    print(f"\n{'─' * 60}", flush=True)
    print(f"  ▶  {msg}", flush=True)
    print(f"{'─' * 60}", flush=True)


def load_companies():
    from shared.supabase_client import fetch_companies
    _step("Loading company list from Supabase")
    companies = fetch_companies()
    if not companies:
        log.warning("No companies found in Supabase — nothing to ingest.")
        sys.exit(0)
    log.info("Found %d companies: %s", len(companies), [c.ticker for c in companies])
    return companies


# ---------------------------------------------------------------------------
# Pipeline runners
# ---------------------------------------------------------------------------


def run_10k_ingestion(companies) -> None:
    _step("10-K Ingestion Pipeline")

    log.debug("Importing 10-K pipeline modules (TenKDownloader, TenKIngestor)…")
    t0 = time.perf_counter()
    from tenk.downloader import TenKDownloader
    from tenk.ingestor import TenKIngestor
    log.debug("Modules loaded in %.1fs", time.perf_counter() - t0)

    log.info("Initialising downloader…")
    downloader = TenKDownloader()

    log.info("Initialising embedder (connecting to ChromaDB, creating collections)…")
    t0 = time.perf_counter()
    ingestor = TenKIngestor()
    log.info("Embedder ready in %.1fs", time.perf_counter() - t0)

    all_stats: list[dict] = []

    for company in companies:
        log.info("[10-K] Processing %s (%s)", company.ticker, company.company_name)

        log.debug("  Downloading filing from SEC EDGAR…")
        file_path = downloader.download(company.ticker)

        if file_path is None:
            log.warning("  No 10-K found for %s — skipping.", company.ticker)
            continue

        log.debug("  Filing cached at: %s", file_path)
        stats = ingestor.ingest(str(file_path), company.company_name, ticker=company.ticker)
        stats["ticker"] = company.ticker
        all_stats.append(stats)
        log.info("  ✓ %s — %d chunks uploaded", company.ticker, stats["total_chunks"])

    print("\n--- 10-K Ingestion Summary ---")
    for s in all_stats:
        print(f"  {s['ticker']} ({s['company']}): {s['total_chunks']} chunks")


def run_news_ingestion(companies) -> None:
    _step("News Ingestion Pipeline")

    log.debug("Importing news pipeline modules (NewsIngestor, FinBERT)…")
    log.debug("  Note: first run downloads the FinBERT model (~500 MB) — this may take a minute.")
    t0 = time.perf_counter()
    from News.ingestor import NewsIngestor
    log.debug("Modules loaded in %.1fs", time.perf_counter() - t0)

    log.info("Initialising ingestor (ChromaDB collections + loading FinBERT)…")
    t0 = time.perf_counter()
    ingestor = NewsIngestor()
    log.info("Ingestor ready in %.1fs", time.perf_counter() - t0)

    all_stats: list[dict] = []

    for company in companies:
        log.info("[News] Processing %s (%s)", company.ticker, company.company_name)
        stats = ingestor.ingest(company.ticker, company.company_name)
        all_stats.append(stats)
        log.info(
            "  ✓ %s — discovered=%d  high=%d  medium=%d  low=%d  chunks=%d  skipped=%d",
            company.ticker,
            stats["total_discovered"],
            stats["ingested_high"],
            stats["ingested_medium"],
            stats["ingested_low"],
            stats["total_chunks"],
            stats["skipped"],
        )

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
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging (default: INFO only).",
    )
    p.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Only process these tickers (e.g. --tickers MSFT TSLA V).",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)

    log.info("=" * 60)
    log.info("  FinsightAI RAG Ingestion  |  mode=%s  verbose=%s", args.mode, args.verbose)
    log.info("=" * 60)

    companies = load_companies()

    if args.tickers:
        filter_set = {t.upper() for t in args.tickers}
        companies = [c for c in companies if c.ticker.upper() in filter_set]
        if not companies:
            log.error("None of the requested tickers found in Supabase: %s", args.tickers)
            sys.exit(1)
        log.info("Filtered to %d ticker(s): %s", len(companies), [c.ticker for c in companies])

    if args.mode in ("10k", "all"):
        run_10k_ingestion(companies)

    if args.mode in ("news", "all"):
        run_news_ingestion(companies)

    print("\n✓ Ingestion complete.")


if __name__ == "__main__":
    main()
