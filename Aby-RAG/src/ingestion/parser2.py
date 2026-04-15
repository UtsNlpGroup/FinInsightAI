from bs4 import BeautifulSoup
import re


def extract_sections(company: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    print(f"***\tExtracting sections from {company}...\t***")

    # -----------------------------
    # REMOVE NOISE
    # -----------------------------
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # -----------------------------
    # CLEAN TEXT
    # -----------------------------
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.encode('utf-8', 'ignore').decode('utf-8')

    text = text.replace("", "'")
    text = text.replace("", '"').replace("", '"')
    text = text.replace("", "'")

    # -----------------------------
    # FIND ALL ITEM POSITIONS
    # -----------------------------
    item1_matches = list(re.finditer(r'Item\s+1\b', text, re.IGNORECASE))
    item1a_matches = list(re.finditer(r'Item\s+1A\b', text, re.IGNORECASE))
    item7_matches = list(re.finditer(r'Item\s+7\b', text, re.IGNORECASE))
    item8_matches = list(re.finditer(r'Item\s+8\b', text, re.IGNORECASE))
    item1b_matches = list(re.finditer(r'Item\s+1B\b', text, re.IGNORECASE))


    # -----------------------------
    # HANDLE MULTIPLE MATCHES (TOC ISSUE)
    # -----------------------------
    def get_valid_match(matches, text):
        if not matches:
            return None

        for match in matches:
            start = match.start()

            # Skip very early matches (TOC zone)
            if start < len(text) * 0.1:
                continue

            # Check if this match leads to meaningful content
            snippet = text[start:start + 2000]

            if len(snippet) > 1000:
                return match

        # fallback
        return matches[0]

    item1 = get_valid_match(item1_matches, text)
    item1a = get_valid_match(item1a_matches, text)
    item7 = get_valid_match(item7_matches, text)
    item8 = get_valid_match(item8_matches, text)
    item1b = get_valid_match(item1b_matches, text)

    sections = {}

    # -----------------------------
    # BUSINESS: Item 1 → Item 1A
    # -----------------------------
    if item1 and item1a:
        content = text[item1.start():item1a.start()]
        content = re.sub(r'^Business\s*', '', content, flags=re.IGNORECASE)
        sections["business"] = content

    # -----------------------------
    # RISK: Item 1A → Item 7
    # -----------------------------
    if item1a and item1b:
        content = text[item1a.start():item1b.start()]
        content = re.sub(r'^Risk Factors\s*', '', content, flags=re.IGNORECASE)
        sections["risk"] = content

    # -----------------------------
    # MDA: Item 7 → Item 8
    # -----------------------------
    if item7 and item8:
        content = text[item7.start():item8.start()]
        content = re.sub(r'^Management.*Analysis\s*', '', content, flags=re.IGNORECASE)
        sections["mda"] = content

    return sections