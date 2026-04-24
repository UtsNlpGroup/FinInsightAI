from src.ingestion.loader import load_html
from src.ingestion.parser import extract_sections


def debug_sections(file_path: str, company: str):
    print(f"\n🔍 Debugging: {company}\n")

    html = load_html(file_path)
    sections = extract_sections(company, html)

    for name, content in sections.items():
        print("\n====================================")
        print(f"Section: {name}")
        print(f"Length: {len(content)} characters")

        print("\n--- START ---")
        print(content[:1500])

        print("\n--- END ---")
        print(content[-1500:])


if __name__ == "__main__":
    company = input("Enter company name (e.g., Apple, Tesla): ")
    file_path = f"data/{company}.html"
    debug_sections(file_path, company)