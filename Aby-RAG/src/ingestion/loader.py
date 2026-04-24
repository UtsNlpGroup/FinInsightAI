from pathlib import Path

# def load_html(path: str) -> str:
#     try:
#         with open(path, "r", encoding="utf-8") as f:
#             return f.read()
#     except UnicodeDecodeError:
#         with open(path, "r", encoding="latin-1") as f:
#             return f.read()

def load_html(path: str) -> str:
    file_name = Path(path).name
    print(f"\n=== {path} ===")
    html = Path('data') / file_name
    text = html.read_text(encoding='utf-8', errors='ignore')
    # print(len(text))
    # print(text[:500])
    # print("\n\n..Start text above and end text below..\n\n")
    # print(text[-500:])
    return text