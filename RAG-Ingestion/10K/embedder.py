from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from shared import config as cfg
from shared.chroma_client import ChromaClientConfig, ChromaClientFactory


class TenKEmbedder:
    """
    Wraps the HuggingFace BGE embedding model and the remote Chroma vector store
    for 10-K document upload.

    Uses ChromaClientFactory from shared to avoid duplicating the connection logic.
    """

    def __init__(
        self,
        collection_name: str = cfg.DEFAULT_10K_COLLECTION,
        embedding_model_name: str = cfg.DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self._collection_name = collection_name
        self._embedding_model = HuggingFaceEmbeddings(
            model_name=embedding_model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        client_config = ChromaClientConfig.from_env()
        self._chroma_client = ChromaClientFactory.create(client_config)

    def upload(self, documents: list[Document]) -> None:
        """
        Embed and upload a list of LangChain Documents to the Chroma collection.

        Args:
            documents: Chunked Document objects produced by TenKChunker.
        """
        if not documents:
            print("No documents to upload — skipping.")
            return

        vectorstore = Chroma(
            client=self._chroma_client,
            collection_name=self._collection_name,
            embedding_function=self._embedding_model,
        )

        print(f"Uploading {len(documents)} chunks to collection '{self._collection_name}'...")
        vectorstore.add_documents(documents)
        print("Upload complete.")
