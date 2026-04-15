from collections import Counter
from time import time

from dotenv import load_dotenv
import os

load_dotenv()

from src.ingestion.loader import load_html
from src.ingestion.parser import extract_sections
from src.ingestion.chunker import create_documents
# from src.rag.embedder import create_vectorstore
from src.rag.embedder import get_or_create_vectorstore
from src.rag.retriever import retrieve_documents
from src.rag.qa import generate_answer
from src.rag.qa import generate_final_insight
from src.utils.logger import save_results






model = input("Enter model to use (ollama or openai or ollama2): ").strip().lower()
MODEL_TYPE = model   # or "openai"

QUESTION_CONFIG = [
    {
        "question": "What are the company's core business segments and primary revenue drivers?",
        "section": "business"
    },
    {
        "question": "What are the most significant risks and emerging uncertainties that could impact future performance?",
        "section": "risk"
    },
    {
        "question": "What are the key growth drivers, strategic initiatives, and competitive advantages highlighted by management?",
        "section": "mda"
    },
    {
        "question": "What factors drove the company's financial performance, and what major challenges or headwinds were reported?",
        "section": "mda"
    },
    {
        "question": "What signals does management provide about the company's future outlook, including potential growth opportunities or risks?",
        "section": "mda"
    }
]





def run_pipeline(file_path: str, company: str):
    # STEP 1: Load
    html = load_html(file_path)

    # STEP 2: Parse
    sections = extract_sections(company, html)

    # -----------------------------
    # 🔍 STEP 2.5: CHECK SECTIONS
    # -----------------------------
    print("\n=== Sections Extracted ===")
    print(sections.keys())

    # -----------------------------
    # STEP 3: Chunk → Documents
    # -----------------------------
    documents = create_documents(sections, company)

    print(f"\nTotal documents: {len(documents)}")

    # -----------------------------
    # 🔍 STEP 4: COUNT PER SECTION
    # -----------------------------
    counts = Counter([doc.metadata["section"] for doc in documents])

    print("\n=== Chunk Count per Section ===")
    for section, count in counts.items():
        print(f"{section}: {count}")

    # -----------------------------
    # 🔍 STEP 5: SAMPLE CHUNKS
    # -----------------------------
    """print("\n=== Sample Chunks (1 per section) ===")

    seen_sections = set()

    for doc in documents:
        section = doc.metadata["section"]

        if section not in seen_sections:
            print("\n--------------------------")
            print(f"Section: {section}")
            print(doc.page_content[:500])  # first 500 chars

            seen_sections.add(section)

        # stop after showing all sections
        if len(seen_sections) == len(counts):
            break"""

    # -----------------------------
    # STEP 6: Create Vector Store
    # -----------------------------
    vectorstore = get_or_create_vectorstore(documents, company=company)

    # -----------------------------
    # 🔍 STEP 7: VERIFY VECTORSTORE
    # -----------------------------
    # print("\n=== Vectorstore Verification ===")

    # # 1. Check collection size
    # collection = vectorstore._collection
    # count = collection.count()
    # print(f"Total vectors stored: {count}")

    # # 2. Run a test similarity search
    # query = "What are the main risks to the company?"

    # results = vectorstore.similarity_search(query, k=3)

    # print("\nTop 3 retrieved chunks:")
    # for i, doc in enumerate(results):
    #     print(f"\nResult {i+1}")
    #     print("Section:", doc.metadata["section"])
    #     print(doc.page_content[:300])

    # -----------------------------
    # STEP 8: RUN RETRIEVAL FOR ALL QUESTIONS
    # -----------------------------
    print("\n=== Running Retrieval for All Questions ===\n\n")

    # for i, q in enumerate(QUESTION_CONFIG):
    #     question = q["question"]
    #     section = q["section"]

    #     print("\n=================NEW QUESTION==================\n")
    #     print(f"Q{i+1}: {question}")
    #     print(f"Section: {section}")

    #     results = retrieve_documents(vectorstore, question, section, company, k=3)

    #     for j, doc in enumerate(results):
    #         print("\n--------------------------")
    #         print(f"Chunk {j+1}")
    #         print(doc.page_content)
    #         print("\nMetadata:", doc.metadata)


    # -----------------------------
    # STEP 9: 
    # -----------------------------
    print("\n=== QA Debug Mode/Generation of answers ===")
    results_data = []
    answers = []

    for i, q in enumerate(QUESTION_CONFIG):
        question = q["question"]
        section = q["section"]

        print("\n===================================")
        print(f"Q{i+1}: {question}")

        # Retrieve
        docs = retrieve_documents(
            vectorstore,
            question,
            section,
            company=company,
            k=3
        )

        # Print chunks (optional)
        # print("\n--- Retrieved Chunks ---")
        # for j, doc in enumerate(docs):
        #     print(f"\nChunk {j+1}")
        #     print(doc.page_content[:200])

        # Generate answer
        answer = generate_answer(question, docs, model_type=MODEL_TYPE)

        print("\n--- Answer ---")
        print(answer)

        # Save structured result
        results_data.append({
            "question": question,
            "section": section,
            "answer": answer,
            # "num_chunks": len(docs)
        })

        answers.append(answer)
    # Save the 5 question results to a file
    # save_results(company, model_name=MODEL_TYPE, results=results_data)

    print("\n\n\n||||||||||||||||||=== Final Investor Insight ===||||||||||||||||||\n\n\n")

    final_report = generate_final_insight(
        answers,
        model_type=MODEL_TYPE
    )

    print(final_report)

    # Save all results including final insight to a file
    save_results(
        company,
        model_name=MODEL_TYPE,
        results={
            "qa_results": results_data,
            "final_insight": final_report
        }
    )



if __name__ == "__main__":
    print("\n=== Starting RAG Pipeline ===\n")
    company = input("Enter the company you want to analyze: ")

    file_path = f"data/{company}.html"

    run_pipeline(file_path, company)

