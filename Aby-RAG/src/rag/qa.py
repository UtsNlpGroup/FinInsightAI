from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.rag.prompts import FINAL_PROMPT, QA_PROMPT


# -----------------------------
# LLM SETUP (OLLAMA)
# -----------------------------
def get_llm(model_type="ollama"):
    if model_type == "ollama":
        # from langchain_ollama import ChatOllama
        return ChatOllama(
            model="gpt-oss:20b",
            temperature=0,
            top_p=0.3
        )

    elif model_type == "openai":
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            top_p=0.3
        )
    elif model_type == "ollama2":
        # from langchain_ollama import ChatOllama
        return ChatOllama(
            model="qwen3:4b",
            temperature=0,
            top_p=0.3
        )


# -----------------------------
# PROMPT TEMPLATE
# -----------------------------
def get_prompt():
    return ChatPromptTemplate.from_template(QA_PROMPT)


# -----------------------------
# GENERATE ANSWER
# -----------------------------
def generate_answer(question: str, documents, model_type):

    llm = get_llm(model_type)
    prompt = get_prompt()

    context = "\n\n".join([doc.page_content for doc in documents])

    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return response.content



# -----------------------------
# GENERATE FINAL INSIGHT
# -----------------------------


def generate_final_insight(answers, model_type="ollama2"):

    llm = get_llm(model_type)

    combined_answers = "\n\n".join([
        f"Q{i+1}: {ans}" for i, ans in enumerate(answers)
    ])

    prompt = FINAL_PROMPT.format(combined_answers=combined_answers)

    response = llm.invoke(prompt)

    return response.content