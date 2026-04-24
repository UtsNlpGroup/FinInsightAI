from pathlib import Path
from src.ingestion.parser import extract_sections

for file_name in ['Tesla.html', 'Apple.html', 'Nvidia.html']:
    print(f"\n=== {file_name} ===")
    html = Path('data') / file_name
    text = html.read_text(encoding='utf-8', errors='ignore')
    print(len(text))
    print(text[:500])
    print("\n\n..Start text above and end text below..\n\n")
    print(text[-500:])
    sections = extract_sections(file_name.replace('.html', ''), text)
    for section_name, content in sections.items():
        print(f"[{section_name}] length={len(content)} words={len(content.split())}")
        sample = content[:450].replace('\n', ' ')
        print(f"sample: {sample}\n")
