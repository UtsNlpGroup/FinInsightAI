import chromadb
from chromadb.utils import embedding_functions
from langchain_core.documents import Document

from shared import config as cfg
from shared.chroma_client import ChromaClientConfig, ChromaClientFactory


class TenKEmbedder:
    """
    Uploads 10-K chunks to the remote Chroma vector store using the same
    DefaultEmbeddingFunction (all-MiniLM-L6-v2) as the news pipeline,
    so both collections share an identical embedding space.
    """

    def __init__(self, collection_name: str = cfg.DEFAULT_10K_COLLECTION) -> None:
        self._collection_name = collection_name

        client_config = ChromaClientConfig.from_env()
        chroma_client = ChromaClientFactory.create(client_config)

        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self._collection: chromadb.Collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=emb_fn,
        )

    def upload(self, documents: list[Document]) -> None:
        """
        Add new chunks to the Chroma collection, skipping any whose ID already
        exists — the same deduplication strategy used by the news pipeline.

        Args:
            documents: Chunked Document objects produced by TenKChunker.
        """
        if not documents:
            print("[TenKEmbedder] No documents to upload — skipping.")
            return

        all_ids = [doc.metadata["id"] for doc in documents]

        existing = self._collection.get(ids=all_ids, include=[])
        existing_ids = set(existing["ids"])

        new_docs = [doc for doc in documents if doc.metadata["id"] not in existing_ids]

        print(
            f"[TenKEmbedder] {len(documents)} chunks total — "
            f"{len(existing_ids)} already exist, {len(new_docs)} new."
        )

        if not new_docs:
            print("[TenKEmbedder] All chunks already in vector store — skipping upload.")
            return

        self._collection.add(
            ids=[doc.metadata["id"] for doc in new_docs],
            documents=[doc.page_content for doc in new_docs],
            metadatas=[doc.metadata for doc in new_docs],
        )
        print(f"[TenKEmbedder] Uploaded {len(new_docs)} new chunks to '{self._collection_name}'.")
