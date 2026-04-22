# from pathlib import Path

# path = 'data/Tesla.html'

# file_name = Path(path).name
# print(f"\n=== {file_name} ===")

# # write code so that file_name should only contain the file name not the path
# html = Path('data') / file_name


# from src.ingestion.loader import load_html

# path = 'data/Tesla.html'

# print(load_html(path))

# Path to .env location containing the Chroma API keys


from dotenv import load_dotenv
import os
import chromadb


env_path = ".env"

# 1. Parse the .env file and retrieve the API keys
if load_dotenv(env_path):
    print("✅ Environment variables loaded from .env")
else:
    print("❌ Failed to load .env - Check if the file exists!")

CF_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID")
CF_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET")
CHROMA_URL = os.getenv("CHROMA_HOST")

print(f"Chroma URL: {CHROMA_URL}")

# 2. Setup the Client with Custom Headers
client = chromadb.HttpClient(
    host=CHROMA_URL,                              # Your Cloudflare URL
    port=443,                                     # Standard HTTPS port
    ssl=True,                                     # MUST be True for Cloudflare
    headers={
        "CF-Access-Client-Id": CF_CLIENT_ID,
        "CF-Access-Client-Secret": CF_CLIENT_SECRET
    },
)

# 3. Test the connection
print(f"Connection Heartbeat: {client.heartbeat()}")