import os

import chromadb
from chromadb.utils import embedding_functions
from langchain_core.documents import Document

from shared import config as cfg
from shared.chroma_client import ChromaClientConfig, ChromaClientFactory


class TenKEmbedder:
    """
    Uploads 10-K chunks to two Chroma collections in parallel:

      - sec_filings_chroma  →  DefaultEmbeddingFunction (all-MiniLM-L6-v2)
      - sec_filings_openai  →  OpenAIEmbeddingFunction  (text-embedding-3-small)

    Each collection is deduped independently using the chunk's deterministic ID,
    so partial failures from a previous run are automatically healed on the next run.
    """

    def __init__(
        self,
        chroma_collection_name: str = cfg.DEFAULT_10K_COLLECTION_CHROMA,
        openai_collection_name: str = cfg.DEFAULT_10K_COLLECTION_OPENAI,
    ) -> None:
        client_config = ChromaClientConfig.from_env()
        chroma_client = ChromaClientFactory.create(client_config)

        self._collections: list[chromadb.Collection] = [
            chroma_client.get_or_create_collection(
                name=chroma_collection_name,
                embedding_function=embedding_functions.DefaultEmbeddingFunction(),
            ),
            chroma_client.get_or_create_collection(
                name=openai_collection_name,
                embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                    api_key=os.environ["OPENAI_API_KEY"],
                    model_name="text-embedding-3-small",
                ),
            ),
        ]

    def upload(self, documents: list[Document]) -> None:
        """
        Add new chunks to both Chroma collections, skipping any whose ID already
        exists in each collection — deduplication is done per-collection so a
        partial failure on a previous run is automatically retried.

        Args:
            documents: Chunked Document objects produced by TenKChunker.
        """
        if not documents:
            print("[TenKEmbedder] No documents to upload — skipping.")
            return

        all_ids = [doc.metadata["id"] for doc in documents]

        for collection in self._collections:
            existing_ids = set(collection.get(ids=all_ids, include=[])["ids"])
            new_docs = [doc for doc in documents if doc.metadata["id"] not in existing_ids]

            print(
                f"[TenKEmbedder] '{collection.name}': "
                f"{len(documents)} total — {len(existing_ids)} exist, {len(new_docs)} new."
            )

            if not new_docs:
                print(f"[TenKEmbedder] All chunks already in '{collection.name}' — skipping.")
                continue

            collection.add(
                ids=[doc.metadata["id"] for doc in new_docs],
                documents=[doc.page_content for doc in new_docs],
                metadatas=[doc.metadata for doc in new_docs],
            )
            print(f"[TenKEmbedder] Uploaded {len(new_docs)} chunks to '{collection.name}'.")
