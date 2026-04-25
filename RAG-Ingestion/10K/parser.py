"""
Extracts plain text from a 10-K filing document.

Handles both HTML/HTM filings (strips tags via BeautifulSoup) and plain-text /
SGML submissions (normalises whitespace directly).
"""

import re

from bs4 import BeautifulSoup


class TenKParser:
    """
    Converts a raw filing document (HTML or plain text) into a single clean
    plain-text string ready for chunking.
    """

    def parse(self, company: str, content: str) -> str:
        """
        Extract clean plain text from a filing document.

        Args:
            company: Company name (used for logging only).
            content: Raw file contents — HTML, HTM, or plain text.

        Returns:
            Normalised plain-text string.
        """
        print(f"[TenKParser] Extracting plain text for {company}...")

        if self._looks_like_html(content):
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
        else:
            text = content

        text = self._normalise(text)
        print(f"[TenKParser] Extracted {len(text):,} characters.")
        return text

    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_html(content: str) -> bool:
        return bool(re.search(r"<\s*(html|body|div|p|span|table)\b", content[:2000], re.IGNORECASE))

    @staticmethod
    def _normalise(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
