import yfinance as yf

from shared import config as cfg


class NewsCollector:
    """
    Discovers financial news articles for a given ticker using Yahoo Finance.

    Three overlapping search queries are run per company to maximise recall,
    then results are deduplicated by Yahoo's article UUID.
    """

    def __init__(self, news_count: int = cfg.DEFAULT_NEWS_COUNT) -> None:
        self._news_count = news_count

    def collect(self, ticker: str, company_name: str) -> list[dict]:
        """
        Build a deduplicated news pool for the given ticker/company.

        Args:
            ticker:       Stock ticker symbol (e.g. 'NVDA').
            company_name: Human-readable company name (e.g. 'Nvidia').

        Returns:
            List of unique news item dicts (each has 'uuid', 'title', 'link',
            'publisher', 'providerPublishTime', 'relatedTickers', 'summary').
        """
        queries = [ticker, company_name, f"{company_name} stock"]

        pool: dict[str, dict] = {}
        for query in queries:
            results = yf.Search(query, news_count=self._news_count).news
            for item in results:
                pool[item["uuid"]] = item

        unique_articles = list(pool.values())
        print(f"[NewsCollector] {ticker}: {len(unique_articles)} unique articles discovered.")
        return unique_articles
