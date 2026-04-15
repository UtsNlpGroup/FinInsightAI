import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


PERSIST_DIR = "chroma_db"


def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


def get_or_create_vectorstore(documents, company):
    embedding_model = get_embedding_model()

    # -----------------------------
    # LOAD EXISTING DB
    # -----------------------------
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        print("\n📂 Loading existing vector store...")
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embedding_model
        )

        # 🔍 Check if company already exists
        existing = vectorstore.get(
            where={"company": company}
        )

        if existing["ids"]:
            print(f"⚠️ Data for {company} already exists. Skipping embedding.")
        else:
            print(f"➕ Adding new data for {company}...")
            vectorstore.add_documents(documents)

    else:
        # -----------------------------
        # CREATE NEW DB
        # -----------------------------
        print("\n🆕 Creating new vector store...")
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding_model,
            persist_directory=PERSIST_DIR
        )
        print("\n✅ Vector store created successfully!")

    return vectorstore