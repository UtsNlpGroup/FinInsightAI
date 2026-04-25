import time

import chromadb
from chromadb.utils import embedding_functions

from shared import config as cfg
from shared.base_ingestor import BaseIngestor
from shared.chroma_client import ChromaClientConfig, ChromaClientFactory
from News.collector import NewsCollector
from News.scraper import ArticleScraper
from News.chunker import NewsChunker
from News.sentiment import FinBERTSentiment


class NewsIngestor(BaseIngestor):
    """
    Orchestrates the full news ingestion pipeline for one ticker:
      Discover → Scrape → Tier text → FinBERT sentiment → Chunk → Upload to Chroma.

    Tiering strategy:
      - high:   Full scraped article text
      - medium: Yahoo summary/description
      - low:    Synthetic headline document (paywalled articles)

    FinBERT runs on the representative text for each article (full text when
    available, summary otherwise, headline for low-quality) and stores:
      sentiment_label, sentiment_score, sentiment_positive,
      sentiment_negative, sentiment_neutral
    as metadata on every chunk belonging to that article.

    The skip-if-seen guard queries the collection for the article's
    `original_uuid` before processing, ensuring idempotent runs.
    """

    def __init__(
        self,
        collection_name: str = cfg.DEFAULT_NEWS_COLLECTION,
        collector: NewsCollector | None = None,
        scraper: ArticleScraper | None = None,
        chunker: NewsChunker | None = None,
        sentiment: FinBERTSentiment | None = None,
        rate_limit_sleep: float = cfg.DEFAULT_RATE_LIMIT_SLEEP,
    ) -> None:
        self._collector = collector or NewsCollector()
        self._scraper = scraper or ArticleScraper()
        self._chunker = chunker or NewsChunker()
        self._sentiment = sentiment or FinBERTSentiment()
        self._rate_limit_sleep = rate_limit_sleep

        client_config = ChromaClientConfig.from_env()
        chroma_client = ChromaClientFactory.create(client_config)

        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self._collection: chromadb.Collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=emb_fn,
        )

    def ingest(self, ticker: str, company_name: str) -> dict:
        """
        Ingest all discoverable news articles for the given ticker.

        Args:
            ticker:       Stock ticker symbol (e.g. 'NVDA').
            company_name: Human-readable company name (e.g. 'Nvidia').

        Returns:
            Stats dict with keys: ticker, total_discovered, skipped,
            ingested_high, ingested_medium, ingested_low, total_chunks.
        """
        print(f"\n[NewsIngestor] Starting ingestion for {ticker} ({company_name})")

        articles = self._collector.collect(ticker, company_name)

        stats = {
            "ticker": ticker,
            "total_discovered": len(articles),
            "skipped": 0,
            "ingested_high": 0,
            "ingested_medium": 0,
            "ingested_low": 0,
            "total_chunks": 0,
        }

        for item in articles:
            article_uuid = item["uuid"]

            existing = self._collection.get(where={"original_uuid": article_uuid}, limit=1)
            if existing["ids"]:
                stats["skipped"] += 1
                continue

            base_metadata = {
                "ticker": ticker,
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "publisher": item.get("publisher", ""),
                "published": item.get("providerPublishTime", ""),
                "original_uuid": article_uuid,
            }

            full_text = self._scraper.scrape(item.get("link", ""), ticker, company_name)

            if full_text:
                sentiment_text = full_text
                chunks = self._chunker.chunk(full_text, base_metadata, quality="high")
                tier = "ingested_high"
                print(f"  [high]   {item.get('title', '')[:60]}...")
            else:
                summary = item.get("summary") or item.get("description", "")
                if summary and len(summary) > cfg.DEFAULT_MIN_SUMMARY_CHARS:
                    sentiment_text = summary
                    chunks = self._chunker.chunk(summary, base_metadata, quality="medium")
                    tier = "ingested_medium"
                    print(f"  [medium] {item.get('title', '')[:60]}...")
                else:
                    pub = item.get("publisher", "Unknown Source")
                    related = ", ".join(item.get("relatedTickers", []))
                    headline = item.get("title", "No Headline")
                    synthetic_doc = (
                        f"Financial News Headline from {pub}: {headline}. "
                        f"Related Assets: {related}."
                    )
                    sentiment_text = synthetic_doc
                    chunks = self._chunker.chunk(synthetic_doc, base_metadata, quality="low")
                    tier = "ingested_low"
                    print(f"  [low]    {headline[:60]}...")

            # Run FinBERT on the representative text and attach to every chunk
            sentiment_fields = self._sentiment.analyse(sentiment_text)
            print(
                f"         sentiment={sentiment_fields['sentiment_label']} "
                f"(score={sentiment_fields['sentiment_score']:+.3f})"
            )
            for chunk in chunks:
                chunk["metadata"].update(sentiment_fields)

            if chunks:
                self._collection.add(
                    ids=[c["id"] for c in chunks],
                    documents=[c["document"] for c in chunks],
                    metadatas=[c["metadata"] for c in chunks],
                )
                stats[tier] += 1
                stats["total_chunks"] += len(chunks)

            time.sleep(self._rate_limit_sleep)

        print(
            f"[NewsIngestor] Done for {ticker}. "
            f"Discovered={stats['total_discovered']}, "
            f"Skipped={stats['skipped']}, "
            f"High={stats['ingested_high']}, "
            f"Medium={stats['ingested_medium']}, "
            f"Low={stats['ingested_low']}, "
            f"Chunks={stats['total_chunks']}"
        )
        return stats
