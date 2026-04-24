import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

CF_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID")
CF_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET")
CHROMA_URL = os.getenv("CHROMA_HOST")

print(f"Chroma URL: {CHROMA_URL}")
print(f"Client ID loaded: {CF_CLIENT_ID is not None}")

def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


def get_vectorstore(documents=None, collection_name="sec_filings"):

    embedding_model = get_embedding_model()

    # -----------------------------
    # CONNECT TO CHROMA CLOUD
    # -----------------------------
    client = chromadb.HttpClient(
    host="chroma.taskcomply.com",
    port=443,
    ssl=True,
    headers={
        "CF-Access-Client-Id": CF_CLIENT_ID,
        "CF-Access-Client-Secret": CF_CLIENT_SECRET
            },
    )

    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embedding_model
    )

    # -----------------------------
    # ADD DOCUMENTS (optional)
    # -----------------------------
    if documents:
        print("\n📤 Uploading documents to Chroma Cloud...")
        vectorstore.add_documents(documents)

    return vectorstore
