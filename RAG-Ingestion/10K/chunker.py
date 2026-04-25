import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from shared import config as cfg


class TenKChunker:
    """
    Splits a plain-text 10-K filing into overlapping chunks.

    Each chunk gets a deterministic UUID v5 derived from "{ticker}_{chunk_text}"
    so that re-running the pipeline never creates duplicate vector-store entries.
    """

    def __init__(
        self,
        chunk_size: int = cfg.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = cfg.DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text: str, company: str, ticker: str = "") -> list[Document]:
        """
        Split plain text into LangChain Documents.

        Args:
            text:    Full plain-text content of the 10-K filing.
            company: Company name stored in each chunk's metadata.
            ticker:  Stock ticker symbol stored in each chunk's metadata.

        Returns:
            List of Document objects ready for vector-store upload.
        """
        prefix = ticker if ticker else company
        chunks = self._splitter.split_text(text)

        documents = []
        for chunk in chunks:
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{prefix}_{chunk}"))
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "id": chunk_id,
                        "ticker": ticker,
                        "company": company,
                        "source": f"{company} 10-K",
                    },
                )
            )

        return documents
