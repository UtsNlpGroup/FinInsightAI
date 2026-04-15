from langchain_core.documents import Document
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter

def create_documents(sections: dict, company: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    documents = []

    for section_name, content in sections.items():
        chunks = splitter.split_text(content)

        for chunk in chunks:
            documents.append(
                                Document(
                                    page_content=chunk,
                                    metadata={
                                        "company": company,
                                        "section": section_name,
                                        "source": f"{company} 10-K",
                                        "id": str(uuid.uuid4())  # ✅ unique ID
                                    }
                                )
                            )

    return documents