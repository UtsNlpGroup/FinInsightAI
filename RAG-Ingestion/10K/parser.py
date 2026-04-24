import re

from bs4 import BeautifulSoup, NavigableString, Tag


class TenKParser:
    """
    Parses 10-K SEC filings (HTML) and extracts three key sections:
      - business  (Item 1)
      - risk      (Item 1A)
      - mda       (Item 7 — MD&A)

    All DOM-traversal helpers are private methods of this class.
    """

    # Patterns used to identify section heading nodes
    _HEADING_PATTERNS = {
        "business": re.compile(r"^\s*Item\s*1\.\s*Business", re.IGNORECASE),
        "risk": re.compile(r"^\s*Item\s*1A\.\s*Risk\s*Factors", re.IGNORECASE),
        "mda": re.compile(
            r"^\s*Item\s*7\.\s*Management(?:'s|s)?\s+Discussion\s+and\s+Analysis",
            re.IGNORECASE,
        ),
        "item_1b": re.compile(r"^\s*Item\s*1B\.", re.IGNORECASE),
        "item_8": re.compile(r"^\s*Item\s*8\.", re.IGNORECASE),
    }

    _NORMALIZED_KEYS = {
        "business": "item1business",
        "risk": "item1ariskfactors",
        "mda": "item7managementsdiscussionanalysis",
        "item_1b": "item1b",
        "item_8": "item8",
    }

    def parse(self, company: str, html: str) -> dict[str, str]:
        """
        Extract the business, risk, and mda sections from a 10-K HTML document.

        Args:
            company: Company name (used for logging only).
            html:    Raw HTML string of the 10-K filing.

        Returns:
            dict with keys 'business', 'risk', 'mda'; values are cleaned text strings.
        """
        soup = BeautifulSoup(html, "html.parser")
        print(f"***\tExtracting sections from {company}...\t***")

        for tag in soup(["script", "style"]):
            tag.decompose()

        headings = self._find_section_headings(soup)

        stop_containers: set = set()
        for node in headings.values():
            container = self._section_container(node)
            if container is not None:
                stop_containers.add(container)

        sections = {"business": "", "risk": "", "mda": ""}

        if "business" in headings and "risk" in headings:
            sections["business"] = self._collect_section_text(
                headings["business"], stop_containers
            )

        if "risk" in headings:
            if "item_1b" in headings:
                sections["risk"] = self._collect_section_text(
                    headings["risk"], stop_containers
                )
            elif "mda" in headings:
                sections["risk"] = self._fallback_extract(
                    self._normalize_text(soup.get_text(separator=" ")),
                    r"Item\s*1A\.\s*Risk\s*Factors",
                    r"Item\s*7\.",
                )

        if "mda" in headings:
            if "item_8" in headings:
                sections["mda"] = self._collect_section_text(
                    headings["mda"], stop_containers
                )
            else:
                sections["mda"] = self._fallback_extract(
                    self._normalize_text(soup.get_text(separator=" ")),
                    r"Item\s*7\.\s*Management(?:'s|s)?\s+Discussion\s+and\s+Analysis",
                    r"Item\s*8\.",
                )

        for section_name, content in sections.items():
            content = self._normalize_text(content)
            content = re.sub(
                r"^Item\s*\d+[A-Z]?\.\s*.*?\s+", "", content, flags=re.IGNORECASE
            )
            sections[section_name] = content.strip()

        return sections

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\xa0", " ")
        text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2122", "'")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _gather_inline_heading_text(self, node: NavigableString, max_segments: int = 6) -> str:
        pieces = []
        seen_tags = 0

        for el in node.next_elements:
            if el is node:
                continue

            if isinstance(el, NavigableString):
                text = self._normalize_text(el)
                if text:
                    pieces.append(text)
            elif isinstance(el, Tag):
                if el.name in {"div", "p", "table", "tr", "td", "br"} and pieces:
                    break
                if el.name in {"span", "b", "strong"}:
                    text = self._normalize_text(el.get_text(" ", strip=True))
                    if text:
                        pieces.append(text)
                seen_tags += 1
                if seen_tags >= max_segments:
                    break

            if len(pieces) >= max_segments:
                break

        return " ".join(pieces)

    def _normalize_heading_candidate(self, text: str) -> str:
        cleaned = self._normalize_text(text)
        cleaned = re.sub(r"\b([A-Z])\s+([A-Z][A-Za-z]+)", r"\1\2", cleaned)
        return cleaned

    def _find_section_headings(self, soup: BeautifulSoup) -> dict:
        found: dict = {}

        for node in soup.find_all(
            string=re.compile(
                r"Item\s*1A\.|Item\s*1B\.|Item\s*1\.|Item\s*7\.|Item\s*8\.",
                re.IGNORECASE,
            )
        ):
            if not isinstance(node, NavigableString):
                continue

            text = self._normalize_text(node)
            if not text:
                continue

            if node.parent.name == "a" and len(text.split()) <= 2:
                continue

            if len(text.split()) <= 3:
                extra = self._gather_inline_heading_text(node)
                candidate = (
                    self._normalize_heading_candidate(f"{text} {extra}")
                    if extra
                    else self._normalize_heading_candidate(text)
                )
            else:
                candidate = self._normalize_heading_candidate(text)

            dense_candidate = re.sub(r"[^A-Za-z0-9]+", "", candidate).lower()

            for label, pattern in self._HEADING_PATTERNS.items():
                if pattern.search(candidate):
                    found[label] = node
                    break
                if dense_candidate.startswith("item") and self._NORMALIZED_KEYS[label] in dense_candidate:
                    found[label] = node
                    break

        return found

    def _section_container(self, node: NavigableString):
        if node is None:
            return None

        if not isinstance(node.parent, Tag):
            return node.parent

        for ancestor in node.parents:
            if ancestor.name in {"div", "p", "td", "th", "li"} and ancestor.next_sibling is not None:
                return ancestor

        for ancestor in node.parents:
            if ancestor.name in {"div", "p", "td", "th", "li"}:
                return ancestor

        return node.parent

    def _collect_section_text(self, start_node: NavigableString, stop_containers: set) -> str:
        container = self._section_container(start_node)
        if container is None:
            return ""

        pieces = []
        current = container.next_sibling

        while current is not None:
            if isinstance(current, Tag) and current in stop_containers:
                break
            if isinstance(current, Tag):
                pieces.append(current.get_text("\n", strip=True))
            elif isinstance(current, NavigableString):
                pieces.append(str(current).strip())
            current = current.next_sibling

        return "\n".join(pieces)

    def _fallback_extract(self, text: str, start_pattern: str, end_pattern: str) -> str:
        starts = [m.start() for m in re.finditer(start_pattern, text, re.IGNORECASE)]
        ends = [m.start() for m in re.finditer(end_pattern, text, re.IGNORECASE)]

        if not starts or not ends:
            return ""

        for start in starts:
            candidates = [end for end in ends if end > start]
            if candidates:
                return text[start : candidates[0]]

        return ""
