from dotenv import load_dotenv
import os
import chromadb

load_dotenv()

CF_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID")
CF_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET")
CHROMA_URL = os.getenv("CHROMA_HOST")

print(f"Chroma URL: {CHROMA_URL}")
print(f"Client ID loaded: {CF_CLIENT_ID is not None}")

# client = chromadb.HttpClient(
#     host=CHROMA_URL,
#     # port=443,
#     # ssl=True,
#     headers={
#         "CF-Access-Client-Id": CF_CLIENT_ID,
#         "CF-Access-Client-Secret": CF_CLIENT_SECRET
#     },
# )
import httpx

client = chromadb.HttpClient(
    host="chroma.taskcomply.com",
    port=443,
    ssl=True,
    headers={
        "CF-Access-Client-Id": CF_CLIENT_ID,
        "CF-Access-Client-Secret": CF_CLIENT_SECRET
    },
)

client._session = httpx.Client()
print(f"Connection Heartbeat: {client.heartbeat()}")