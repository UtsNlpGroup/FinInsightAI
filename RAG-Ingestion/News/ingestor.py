import os
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

    The same chunks are written to two collections:
      - news_chroma  →  DefaultEmbeddingFunction (all-MiniLM-L6-v2)
      - news_openai  →  OpenAIEmbeddingFunction  (text-embedding-3-small)

    Tiering strategy:
      - high:   Full scraped article text
      - medium: Yahoo summary/description
      - low:    Synthetic headline document (paywalled articles)

    FinBERT runs on the representative text for each article (full text when
    available, summary otherwise, headline for low-quality) and stores:
      sentiment_label, sentiment_score, sentiment_positive,
      sentiment_negative, sentiment_neutral
    as metadata on every chunk belonging to that article.

    The skip-if-seen guard checks both collections before processing; an article
    is skipped only when it already exists in both, so partial failures from a
    previous run are automatically healed on the next run.
    """

    def __init__(
        self,
        chroma_collection_name: str = cfg.DEFAULT_NEWS_COLLECTION_CHROMA,
        openai_collection_name: str = cfg.DEFAULT_NEWS_COLLECTION_OPENAI,
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

        self._chroma_col: chromadb.Collection = chroma_client.get_or_create_collection(
            name=chroma_collection_name,
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )
        self._openai_col: chromadb.Collection = chroma_client.get_or_create_collection(
            name=openai_collection_name,
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ["OPENAI_API_KEY"],
                model_name="text-embedding-3-small",
            ),
        )
        self._collections = [self._chroma_col, self._openai_col]

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

            # Skip only when this (article, ticker) pair already exists in BOTH
            # collections. Scoping by ticker means the same article can be stored
            # once per ticker it is relevant to — cross-ticker news stories (e.g.
            # "AI chip stocks" appearing in both NVDA and AAPL feeds) will be
            # ingested for each ticker so that per-ticker filtered queries work.
            ticker_uuid_filter = {
                "$and": [
                    {"original_uuid": {"$eq": article_uuid}},
                    {"ticker": {"$eq": ticker}},
                ]
            }
            in_chroma = bool(
                self._chroma_col.get(where=ticker_uuid_filter, limit=1)["ids"]
            )
            in_openai = bool(
                self._openai_col.get(where=ticker_uuid_filter, limit=1)["ids"]
            )
            if in_chroma and in_openai:
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
                # Add to each collection that does not already have this article
                for collection, already_present in [
                    (self._chroma_col, in_chroma),
                    (self._openai_col, in_openai),
                ]:
                    if not already_present:
                        collection.add(
                            ids=[c["id"] for c in chunks],
                            documents=[c["document"] for c in chunks],
                            metadatas=[c["metadata"] for c in chunks],
                        )
                        print(f"         → written to '{collection.name}'")

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
