# from pathlib import Path

# path = 'data/Tesla.html'

# file_name = Path(path).name
# print(f"\n=== {file_name} ===")

# # write code so that file_name should only contain the file name not the path
# html = Path('data') / file_name


from src.ingestion.loader import load_html

path = 'data/Tesla.html'

print(load_html(path))