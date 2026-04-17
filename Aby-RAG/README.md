# 📊 Financial RAG System for SEC 10-K Analysis

> Generate analyst-style insights from company filings using Retrieval-Augmented Generation (RAG)

---

## 🚀 Overview

This project implements an end-to-end **Retrieval-Augmented Generation (RAG)** pipeline to extract structured financial insights from SEC 10-K filings.

It is designed to simulate how a **financial analyst interprets annual reports**, enabling automated extraction of:

* Business model insights
* Growth drivers
* Risks and challenges
* Financial signals
* Forward-looking outlook

The system supports multiple companies (e.g., Apple, Tesla, Nvidia) and produces a **coherent investment-style summary**.

---

## 🧠 Key Highlights

* 🔍 **Section-aware retrieval** (Business, Risk, MD&A)
* 🤖 **LLM-powered Q&A pipeline**
* 📈 **Analyst-style final report generation**
* ⚡ Supports both:

  * Local models (Ollama)
  * Cloud models (OpenAI)
* 💾 Automatic result logging (JSON for evaluation & comparison)
* 🔁 Modular and extensible pipeline

---

## 🏗️ System Architecture

```text
SEC 10-K HTML
      ↓
Text Cleaning & Processing
      ↓
Chunking
      ↓
Embeddings (HuggingFace - BGE)
      ↓
Vector Store (ChromaDB)
      ↓
Retriever (Company + Section Filtering)
      ↓
LLM (Ollama / OpenAI)
      ↓
5 Financial Questions
      ↓
Final Analyst Insight Report
```

---

## ❓ Financial Questions Answered

The system extracts insights by answering:

1. What does the company do and how does it generate revenue?
2. What are the most significant risks?
3. What are the key growth drivers and strategic initiatives?
4. What factors influenced financial performance and challenges?
5. What signals does management provide about future outlook?

---

## 🧰 Tech Stack

* **Python**
* **LangChain**
* **ChromaDB (local vector database)**
* **HuggingFace Embeddings (`BAAI/bge-small-en`)**
* **LLMs:**

  * Ollama (e.g., `gpt-oss`, `mistral`)
  * OpenAI (`gpt-4o-mini`)

---

## 📁 Project Structure

```text
.
├── data/                  # Raw 10-K HTML files
├── results/               # Generated outputs (JSON)
├── src/
│   ├── rag/
│   │   ├── parser.py      # Section extraction
│   │   ├── chunker.py     # Text chunking
│   │   ├── embedder.py    # Embeddings + vector DB
│   │   ├── retriever.py   # Retrieval logic
│   │   ├── qa.py          # LLM interaction
│   │   ├── prompts.py     # Prompt templates
│   ├── utils/
│   │   ├── logger.py      # JSON logging
├── main.py                # Pipeline entry point
├── debug.py               # Debugging utilities
├── .env                   # API keys
└── README.md
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <repo>
```

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Configure environment variables

Create a `.env` file:

```bash
OPENAI_API_KEY=your_key_here
```

---

### 4. Run the pipeline

```bash
python main.py
```

---

## 🔁 Model Switching

Easily switch between local and cloud models:

```python
MODEL_TYPE = "ollama"   # or "openai"
```

---

## 📊 Output

* Answers to all financial questions
* Final analyst-style report
* JSON logs for evaluation

Example:

```text
results/
  Apple_openai_20260417_183000.json
```

---

## ⚡ Performance Considerations

* Use smaller local models (`mistral`, `gemma`) for faster testing
* Use OpenAI for higher-quality outputs
* Tune retrieval (`k`) and chunk size for better performance

---

## 🔍 Example Use Case

This system can be used by:

* Individual investors
* Financial analysts
* Research teams

to quickly extract insights from lengthy financial documents.

---

## 🔮 Future Improvements

* UI / dashboard for querying companies
* Multi-company comparison (e.g., Apple vs Tesla)
* Evaluation metrics for LLM outputs
* Cloud vector database integration
* Advanced prompt optimization

---

## 👤 Author

Developed as part of an NLP project focused on applying LLMs to real-world financial analysis.

---

## ⚠️ Disclaimer

This project is for educational purposes only and does not constitute financial advice.
