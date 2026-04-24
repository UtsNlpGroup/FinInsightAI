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




















# import os
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.vectorstores import Chroma


# PERSIST_DIR = "chroma_db"


# def get_embedding_model():
#     return HuggingFaceEmbeddings(
#         model_name="BAAI/bge-small-en",
#         model_kwargs={"device": "cpu"},
#         encode_kwargs={"normalize_embeddings": True}
#     )


# def get_or_create_vectorstore(documents, company):
#     embedding_model = get_embedding_model()

#     # -----------------------------
#     # LOAD EXISTING DB
#     # -----------------------------
#     if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
#         print("\n📂 Loading existing vector store...")
#         vectorstore = Chroma(
#             persist_directory=PERSIST_DIR,
#             embedding_function=embedding_model
#         )

#         # 🔍 Check if company already exists
#         existing = vectorstore.get(
#             where={"company": company}
#         )

#         if existing["ids"]:
#             print(f"⚠️ Data for {company} already exists. Skipping embedding.")
#         else:
#             print(f"➕ Adding new data for {company}...")
#             vectorstore.add_documents(documents)

#     else:
#         # -----------------------------
#         # CREATE NEW DB
#         # -----------------------------
#         print("\n🆕 Creating new vector store...")
#         vectorstore = Chroma.from_documents(
#             documents=documents,
#             embedding=embedding_model,
#             persist_directory=PERSIST_DIR
#         )
#         print("\n✅ Vector store created successfully!")

#     return vectorstore


