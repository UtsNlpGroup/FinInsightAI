from langchain_community.vectorstores import Chroma


# -----------------------------
# FORMAT QUERY FOR BGE MODEL
# -----------------------------
def format_query(query: str) -> str:
    return f"Represent this sentence for searching relevant passages: {query}"


# -----------------------------
# RETRIEVE DOCUMENTS
# -----------------------------
def retrieve_documents(vectorstore, question: str, section: str, company: str, k: int = 5):
    
    formatted_query = format_query(question)

    results = vectorstore.similarity_search(
        formatted_query,
        k=k,
        filter={
                "$and": [
                    {"section": section},
                    {"company": company}
                ]
                }
    )

    return results



'''# -----------------------------
# QUESTION → SECTION MAPPING
# -----------------------------
QUESTION_TO_SECTION = {
    "business": "business",
    "risk": "risk",
    "growth": "mda",
    "strategy": "mda",
    "performance": "mda",
    "challenges": "mda",
    "outlook": "mda"
}


# -----------------------------
# DETECT QUESTION TYPE
# -----------------------------
# def detect_section(question: str) -> str:
#     question = question.lower()

#     if "risk" in question:
#         return "risk"
#     elif "business" in question or "revenue" in question:
#         return "business"
#     else:
#         return "mda"   # default (most questions fall here)


# -----------------------------
# FORMAT QUERY FOR BGE MODEL
# -----------------------------
def format_query(query: str) -> str:
    return f"Represent this sentence for searching relevant passages: {query}"


# -----------------------------
# RETRIEVE DOCUMENTS
# -----------------------------
def retrieve_documents(vectorstore: Chroma, question: str, k: int = 5):
    
    # 1. Detect section
    section = detect_section(question)

    # 2. Format query (important for BGE)
    formatted_query = format_query(question)

    # 3. Retrieve
    results = vectorstore.similarity_search(
        formatted_query,
        k=k,
        filter={"section": section}
    )

    return results, section'''