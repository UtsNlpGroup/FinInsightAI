import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from shared import config as cfg


class TenKChunker:
    """
    Splits 10-K section text into overlapping LangChain Document chunks,
    each tagged with company and section metadata.
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

    def chunk(self, sections: dict[str, str], company: str) -> list[Document]:
        """
        Convert section text into LangChain Documents.

        Args:
            sections: Mapping of section name → text (e.g. {'business': '...', 'risk': '...', 'mda': '...'}).
            company:  Company name embedded in each Document's metadata.

        Returns:
            Flat list of Document objects ready for vector store upload.
        """
        documents: list[Document] = []

        for section_name, content in sections.items():
            if not content.strip():
                continue

            chunks = self._splitter.split_text(content)

            for chunk in chunks:
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "company": company,
                            "section": section_name,
                            "source": f"{company} 10-K",
                            "id": str(uuid.uuid4()),
                        },
                    )
                )

        return documents
