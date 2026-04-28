"""
Extracts plain text from a 10-K filing document.

Handles both HTML/HTM filings (strips tags via BeautifulSoup) and plain-text /
SGML submissions (normalises whitespace directly).

Modern SEC 10-K filings are iXBRL (inline XBRL) documents.  They embed XBRL
machine-readable data inside XML namespace-prefixed tags (ix:header,
xbrli:context, ix:nonNumeric, etc.) alongside the human-readable HTML body.
Plain BeautifulSoup get_text() includes all that XBRL metadata noise.  This
parser strips every namespace-prefixed tag before extraction so only the
readable narrative text survives.
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
            text = self._extract_html(content)
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
    def _extract_html(content: str) -> str:
        """
        Parse HTML/iXBRL content and return only the human-readable text.

        Steps:
          1. Remove <head> (contains XBRL context data, not narrative text).
          2. Remove all namespace-prefixed tags (ix:*, xbrli:*, etc.) — these
             are XBRL machine-readable metadata that BeautifulSoup would include
             in get_text(), producing thousands of junk tokens.
          3. Remove <script>, <style>, and display:none elements.
          4. Extract remaining text.
        """
        soup = BeautifulSoup(content, "html.parser")

        # Drop <head> — it contains XBRL context references, not body text
        for tag in soup(["head", "script", "style"]):
            tag.decompose()

        # Drop every XML-namespaced tag (ix:header, xbrli:context, ix:nonFraction …)
        for tag in soup.find_all(True):
            if tag.name and ":" in tag.name:
                tag.decompose()

        # Drop hidden elements (display:none)
        for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
            tag.decompose()

        return soup.get_text(separator=" ")

    @staticmethod
    def _normalise(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
