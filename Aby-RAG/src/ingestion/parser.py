from bs4 import BeautifulSoup, NavigableString, Tag
import re


def _normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("’", "'").replace("“", '"').replace("”", '"').replace("™", "'")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _gather_inline_heading_text(node: NavigableString, max_segments: int = 6) -> str:
    pieces = []
    seen_tags = 0

    for el in node.next_elements:
        if el is node:
            continue

        if isinstance(el, NavigableString):
            text = _normalize_text(el)
            if text:
                pieces.append(text)
        elif isinstance(el, Tag):
            if el.name in {"div", "p", "table", "tr", "td", "br"} and pieces:
                break
            if el.name in {"span", "b", "strong"}:
                text = _normalize_text(el.get_text(' ', strip=True))
                if text:
                    pieces.append(text)
            seen_tags += 1
            if seen_tags >= max_segments:
                break

        if len(pieces) >= max_segments:
            break

    return ' '.join(pieces)


def _normalize_heading_candidate(text: str) -> str:
    cleaned = _normalize_text(text)
    cleaned = re.sub(r"\b([A-Z])\s+([A-Z][A-Za-z]+)", r"\1\2", cleaned)
    return cleaned


def _find_section_headings(soup: BeautifulSoup) -> dict:
    patterns = {
        "business": re.compile(r'^\s*Item\s*1\.\s*Business', re.IGNORECASE),
        "risk": re.compile(r'^\s*Item\s*1A\.\s*Risk\s*Factors', re.IGNORECASE),
        "mda": re.compile(r"^\s*Item\s*7\.\s*Management(?:'s|s)?\s+Discussion\s+and\s+Analysis", re.IGNORECASE),
        "item_1b": re.compile(r'^\s*Item\s*1B\.', re.IGNORECASE),
        "item_8": re.compile(r'^\s*Item\s*8\.', re.IGNORECASE)
    }

    normalized_keys = {
        "business": "item1business",
        "risk": "item1ariskfactors",
        "mda": "item7managementsdiscussionanalysis",
        "item_1b": "item1b",
        "item_8": "item8"
    }

    found = {}
    for node in soup.find_all(string=re.compile(r'Item\s*1A\.|Item\s*1B\.|Item\s*1\.|Item\s*7\.|Item\s*8\.', re.IGNORECASE)):
        if not isinstance(node, NavigableString):
            continue

        text = _normalize_text(node)
        if not text:
            continue

        if node.parent.name == 'a' and len(text.split()) <= 2:
            continue

        candidate = text
        if len(text.split()) <= 3:
            extra = _gather_inline_heading_text(node)
            candidate = _normalize_heading_candidate(f"{text} {extra}") if extra else _normalize_heading_candidate(text)
        else:
            candidate = _normalize_heading_candidate(text)

        dense_candidate = re.sub(r'[^A-Za-z0-9]+', '', candidate).lower()

        for label, pattern in patterns.items():
            if pattern.search(candidate):
                found[label] = node
                break
            if dense_candidate.startswith('item') and normalized_keys[label] in dense_candidate:
                found[label] = node
                break

    return found


def _section_container(node: NavigableString):
    if node is None:
        return None

    if not isinstance(node.parent, Tag):
        return node.parent

    # Prefer an ancestor block element that has a next sibling.
    for ancestor in node.parents:
        if ancestor.name in {"div", "p", "td", "th", "li"} and ancestor.next_sibling is not None:
            return ancestor

    # Fallback to the nearest block ancestor.
    for ancestor in node.parents:
        if ancestor.name in {"div", "p", "td", "th", "li"}:
            return ancestor

    return node.parent


def _collect_section_text(start_node: NavigableString, stop_containers: set) -> str:
    container = _section_container(start_node)
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


def _fallback_extract(text: str, start_pattern: str, end_pattern: str) -> str:
    starts = [m.start() for m in re.finditer(start_pattern, text, re.IGNORECASE)]
    ends = [m.start() for m in re.finditer(end_pattern, text, re.IGNORECASE)]
    if not starts or not ends:
        return ""

    for start in starts:
        candidates = [end for end in ends if end > start]
        if not candidates:
            continue
        return text[start:candidates[0]]
    return ""


def extract_sections(company: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    print(f"***\tExtracting sections from {company}...\t***")

    for tag in soup(["script", "style"]):
        tag.decompose()

    headings = _find_section_headings(soup)
    stop_containers = set()
    for node in headings.values():
        container = _section_container(node)
        if container is not None:
            stop_containers.add(container)

    sections = {
        "business": "",
        "risk": "",
        "mda": ""
    }

    if "business" in headings and "risk" in headings:
        sections["business"] = _collect_section_text(headings["business"], stop_containers)
    if "risk" in headings:
        if "item_1b" in headings:
            sections["risk"] = _collect_section_text(headings["risk"], stop_containers)
        elif "mda" in headings:
            sections["risk"] = _fallback_extract(
                _normalize_text(soup.get_text(separator=" ")),
                r'Item\s*1A\.\s*Risk\s*Factors',
                r'Item\s*7\.',
            )
    if "mda" in headings:
        if "item_8" in headings:
            sections["mda"] = _collect_section_text(headings["mda"], stop_containers)
        else:
            sections["mda"] = _fallback_extract(
                _normalize_text(soup.get_text(separator=" ")),
                r"Item\s*7\.\s*Management(?:'s|s)?\s+Discussion\s+and\s+Analysis",
                r'Item\s*8\.',
            )

    for section_name, content in sections.items():
        content = _normalize_text(content)
        content = re.sub(r'^Item\s*\d+[A-Z]?\.\s*.*?\s+', '', content, flags=re.IGNORECASE)
        sections[section_name] = content.strip()

    return sections










    """text = soup.get_text(separator="\n")

    # Clean text
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.encode('utf-8', 'ignore').decode('utf-8')

    # common replacements
    text = text.replace("", "'")
    text = text.replace("", '"').replace("", '"')
    text = text.replace("", "'")

    # Split sections
    pattern = r'(Item\s+1A\.|Item\s+1\.|Item\s+7\.)'
    splits = re.split(pattern, text)

    sections = {}

    for i in range(1, len(splits), 2):
        title = splits[i]
        content = splits[i + 1]

        # remove header only at beginning
        content = re.sub(r'^Risk Factors\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^Business\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^Management.*Analysis\s*', '', content, flags=re.IGNORECASE)

        if "Item 1A" in title:
            sections["risk"] = content
        elif "Item 1." in title:
            sections["business"] = content
        elif "Item 7." in title:
            sections["mda"] = content

    return sections"""






"""from bs4 import BeautifulSoup
import re

def extract_sections(company: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    print(f"***\tExtracting sections from {company}...\t***")

    # -----------------------------
    # CLEAN HTML
    # -----------------------------
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)

    # -----------------------------
    # FIND ALL MATCHES
    # -----------------------------
    def find_all(pattern):
        return [m.start() for m in re.finditer(pattern, text, re.IGNORECASE)]

    item1 = find_all(r'Item\s+1\b')
    item1a = find_all(r'Item\s+1A\b')
    item1b = find_all(r'Item\s+1B\b')
    item7 = find_all(r'Item\s+7\b')
    item8 = find_all(r'Item\s+8\b')

    # -----------------------------
    # SKIP TOC → pick match after 10% of doc
    # -----------------------------
    def pick_real(matches):
        for m in matches:
            if m > len(text) * 0.1:
                return m
        return matches[0] if matches else "Could not find section with simple regex."

    # def pick_real(matches, text):
    #     for m in matches:
    #         # look at content after the match
    #         snippet = text[m:m+3000]

    #         # real sections will have actual content, not just TOC numbers
    #         if len(snippet.split()) > 200:   # enough words → real section
    #             return m

        return matches[0] if matches else "Could not find section with simple regex."
    item1 = pick_real(item1, text)
    item1a = pick_real(item1a, text)
    item1b = pick_real(item1b, text)
    item7 = pick_real(item7, text)
    item8 = pick_real(item8, text)

    sections = {}

    # -----------------------------
    # BUSINESS
    # -----------------------------
    if item1 and item1a:
        sections["business"] = text[item1:item1a]

    # -----------------------------
    # RISK
    # -----------------------------
    if item1a and item1b:
        sections["risk"] = text[item1a:item1b]

    # -----------------------------
    # MDA
    # -----------------------------
    if item7 and item8:
        sections["mda"] = text[item7:item8]

    return sections"""