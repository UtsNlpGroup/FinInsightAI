import requests
from bs4 import BeautifulSoup

from shared import config as cfg


class ArticleScraper:
    """
    Fetches and filters the full text of a news article from its URL.

    Relevance is determined by:
      - Ticker/company name presence in the page title, OR
      - Ticker/company name in the first 20 % of the body AND ≥ 3 total mentions.

    Stop-marker logic prevents "Read Next" sections from bleeding into article text.
    """

    _USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    _NOISE_TAGS = ["script", "style", "nav", "footer", "aside", "header"]
    _STOP_MARKERS = [
        "read-next",
        "related-stories",
        "recirc-feed",
        "caas-footer",
        "article-separator",
    ]

    def __init__(
        self,
        timeout: int = cfg.DEFAULT_SCRAPE_TIMEOUT,
        min_chars: int = cfg.DEFAULT_MIN_ARTICLE_CHARS,
    ) -> None:
        self._timeout = timeout
        self._min_chars = min_chars

    def scrape(self, url: str, ticker: str, company_name: str) -> str | None:
        """
        Download and extract article text, returning None if the article is
        irrelevant to the target company or too short to be useful.

        Args:
            url:          Full article URL.
            ticker:       Stock ticker symbol (e.g. 'NVDA').
            company_name: Human-readable company name (e.g. 'Nvidia').

        Returns:
            Clean article text, or None if rejected.
        """
        try:
            response = requests.get(
                url,
                headers={"User-Agent": self._USER_AGENT},
                timeout=self._timeout,
            )
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            for noise in soup.find_all(self._NOISE_TAGS):
                noise.decompose()

            page_text_upper = soup.get_text(separator=" ").upper()
            ticker_upper = ticker.upper()
            name_upper = company_name.upper()

            total_mentions = page_text_upper.count(ticker_upper) + page_text_upper.count(name_upper)
            anchor_zone = page_text_upper[: int(len(page_text_upper) * 0.20)]
            page_title = soup.find("title")
            title_text = page_title.get_text().upper() if page_title else ""

            is_relevant = (
                ticker_upper in title_text
                or name_upper in title_text
                or (
                    (ticker_upper in anchor_zone or name_upper in anchor_zone)
                    and total_mentions >= 3
                )
            )

            if not is_relevant:
                return None

            best_container = None
            max_p = 0
            for div in soup.find_all(["div", "article", "main", "section"]):
                p_count = len(div.find_all("p", recursive=False))
                if p_count > max_p:
                    max_p = p_count
                    best_container = div

            if best_container is None:
                return None

            clean_elements: list[str] = []
            for el in best_container.find_all(["p", "h1", "h2", "h3"]):
                el_classes = (
                    " ".join(el.get("class", []))
                    + " "
                    + " ".join(el.parent.get("class", []))
                )
                if any(marker in el_classes.lower() for marker in self._STOP_MARKERS):
                    break
                txt = el.get_text().strip()
                if len(txt) > 30:
                    clean_elements.append(txt)

            full_text = "\n\n".join(clean_elements)
            return full_text if len(full_text) >= self._min_chars else None

        except Exception:
            return None
