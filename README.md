#**FinsightAI**

FinsightAI is an AI-powered financial insights platform built as a full-stack, containerised application. It combines a conversational React frontend, a FastAPI backend hosting a LangChain ReAct agent, a FastMCP tool server, and a remote ChromaDB vector store to deliver natural-language financial analysis backed by live market data and Retrieval-Augmented Generation (RAG) over SEC 10-K filings and financial news.


<img width="2816" height="1536" alt="Gemini_Generated_Image_8otnjj8otnjj8otn" src="https://github.com/user-attachments/assets/5abd9797-f665-464a-97d1-39a1f23adaee" />

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Tech Stack](#tech-stack)
4. [MCP Tools](#mcp-tools)
5. [RAG Ingestion Pipeline](#rag-ingestion-pipeline)
6. [Running the Full Stack with Docker Compose](#running-the-full-stack-with-docker-compose)
7. [Local Development (without Docker)](#local-development-without-docker)
8. [Backend API Reference](#backend-api-reference)
9. [RAG Evaluation Results](#rag-evaluation-results)
10. [Test Suite](#test-suite)
11. [Deployment](#deployment)
12. [License](#license)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Docker network                              │
│                                                                       │
│  ┌──────────┐    HTTP     ┌───────────────┐    HTTP     ┌──────────┐  │
│  │ frontend │ ──────────► │   backend     │ ──────────► │   MCP    │  │
│  │  :3000   │            │    :8001      │            │  :8080   │  │
│  │  Nginx   │            │ FastAPI +     │            │ FastMCP  │  │
│  └──────────┘            │ LangChain     │            │ 6 tools  │  │
│                          │ ReAct agent   │            └────┬─────┘  │
│                          └───────────────┘                 │        │
│                                                            │        │
│                                              ┌─────────────▼──────┐ │
│                                              │  ChromaDB (remote) │ │
│                                              │  news_openai       │ │
│                                              │  sec_filings_openai│ │
│                                              └────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

| Service | Technology | Host port |
|---|---|---|
| `frontend` | React 19 + Vite + Tailwind CSS v4, served by Nginx | **3000** |
| `backend` | FastAPI + LangChain ReAct agent | **8001** |
| `mcp-server` | FastMCP (6 financial tools) | **8080** |
| `chromadb` | ChromaDB vector store (remote via CHROMA_URL) | — |

Startup order enforced by health-check dependencies:

```
chromadb → mcp-server → backend → frontend
```

---

## Project Structure

```
finsightAI/
│
├── frontend/                        # React + TypeScript + Vite SPA
│   ├── src/
│   │   ├── components/              # UI components (Chat, Dashboard, Charts…)
│   │   ├── pages/                   # Route-level pages
│   │   ├── services/                # API client layer
│   │   ├── context/                 # Auth + conversation context
│   │   └── hooks/                   # Custom React hooks
│   ├── e2e/                         # Playwright end-to-end tests
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── backend/                         # FastAPI + LangChain agent
│   ├── app/
│   │   ├── main.py                  # App factory + lifespan
│   │   ├── core/                    # Config, DI dependencies
│   │   ├── agents/                  # LangChain ReAct agent (FinancialAgentFactory)
│   │   ├── services/                # AgentService + MCPClientManager
│   │   ├── schemas/                 # Pydantic request / response models
│   │   └── api/v1/                  # REST endpoints (agent, analysis, chat)
│   ├── Dockerfile
│   └── requirements.txt
│
├── MCP/                             # FastMCP tool server
│   ├── server.py                    # All 6 MCP tools (see §MCP Tools)
│   ├── Dockerfile
│   └── requirements.txt
│
├── RAG-Ingestion/                   # Offline data ingestion pipeline
│   ├── 10K/                         # SEC 10-K pipeline
│   │   ├── downloader.py            # SEC EDGAR bulk downloader
│   │   ├── parser.py                # HTML → structured text
│   │   ├── chunker.py               # Recursive character text splitting
│   │   ├── embedder.py              # Dual-backend embedder (Chroma / OpenAI)
│   │   └── ingestor.py              # End-to-end 10-K ingestion orchestrator
│   ├── News/                        # Financial news pipeline
│   │   ├── scraper.py               # RSS + HTML article scraper
│   │   ├── chunker.py               # News-optimised chunking (500 chars / 100 overlap)
│   │   ├── ingestor.py              # ChromaDB upsertion with FinBERT sentiment
│   │   └── sentiment.py             # ProsusAI/finbert sentiment scoring
│   ├── shared/
│   │   └── config.py                # Shared constants (chunk sizes, collection names…)
│   └── main.py                      # CLI entry point for ingestion runs
│
├── tests/
│   ├── unit/                        # Pytest unit tests (agent helpers, MCP tools, config)
│   ├── integration/                 # Integration tests (agent service, news ingestor)
│   ├── api/                         # FastAPI endpoint tests
│   ├── e2e/                         # Full-stack end-to-end tests
│   ├── performance/                 # Response-time benchmarks
│   └── rag/                         # RAG quality evaluation suite
│       ├── golden_dataset.json      # 52 hand-crafted Q&A test cases
│       ├── test_ragas_evaluation.py # Pytest-based RAGAS evaluation
│       ├── test_rag.ipynb           # Interactive RAG evaluation notebook
│       └── results/                 # xlsx result files + analysis notebook
│           └── analysis.ipynb       # Full visualisation & scorecard notebook
│
├── notebooks/
│   └── sentiment.ipynb              # FinBERT sentiment exploration notebook
│
├── docker-compose.yml               # Full-stack orchestration
├── pyproject.toml                   # Python project metadata
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Frontend server | Nginx 1.27 |
| Backend framework | FastAPI, Uvicorn |
| AI agent | LangChain ReAct agent (`create_agent`) |
| LLM | OpenAI GPT-4.1 (configurable) |
| MCP integration | FastMCP, `langchain-mcp-adapters` |
| Vector store | ChromaDB (remote HTTP client) |
| Embeddings | OpenAI `text-embedding-3-small` (primary), Chroma default (`all-MiniLM-L6-v2`) |
| Financial data | yfinance (Yahoo Finance) |
| Paper trading | Alpaca Paper Trading API |
| NLP / Sentiment | ProsusAI/finbert (FinBERT) |
| RAG evaluation | RAGAS framework |
| Containerisation | Docker, Docker Compose |
| CI / CD | GitHub Actions → GitHub Pages (frontend) |
| Python | 3.13 (managed via `uv`) |

---

## Models

FinsightAI uses distinct models for each role — inference, embedding, and sentiment — each chosen for the best accuracy-to-cost trade-off at that layer.

### Inference (LLM)

| Model | Role | Notes |
|---|---|---|
| **OpenAI GPT-4.1** | Production agent LLM | Drives the LangChain ReAct agent for all user-facing queries. Configured via `OPENAI_API_KEY` + `LLM_MODEL` env var (default `gpt-4.1`). Used for tool selection, multi-step reasoning, and final answer generation. |
| **OpenAI GPT-4o-mini** | RAG evaluation judge | Used exclusively by the RAGAS evaluation suite (`test_ragas_evaluation.py`) as the judge LLM for faithfulness and answer-relevancy scoring. Chosen for lower evaluation cost while retaining sufficient reasoning quality. |

### Embeddings

| Model | Role | Collection | Notes |
|---|---|---|---|
| **OpenAI `text-embedding-3-small`** | Primary / production embeddings | `sec_filings_openai`, `news_openai` | Generates 1 536-dimension embeddings via the OpenAI API. Used for all production retrieval queries and for the `vector_store` MCP tool in the default configuration. Achieves 100% cosine-similarity pass-rate on the golden dataset. |
| **Chroma default (`all-MiniLM-L6-v2`)** | Secondary / offline embeddings | `sec_filings_chroma`, `news_chroma` | 384-dimension sentence-transformer model bundled with ChromaDB. Runs locally with no API key required. Used as a fallback when the OpenAI API is unavailable and as the baseline in embedding-quality comparisons. Achieves 87.5% cosine-similarity pass-rate. |
| **OpenAI `text-embedding-3-small`** | RAGAS evaluation embeddings | — | Also used inside the RAGAS framework itself for the answer-relevancy metric (embeds synthetic questions to measure alignment with the original query). |

### Sentiment (NLP)

| Model | Role | Notes |
|---|---|---|
| **ProsusAI/finbert** | Financial sentiment analysis | Fine-tuned BERT model (110 M parameters) specialised for financial text. Runs locally via `transformers`. Applied during news ingestion to every article; outputs `positive` / `negative` / `neutral` label plus individual class probability scores stored as chunk metadata. |

---

## MCP Tools

The FastMCP server (`MCP/server.py`) exposes six tools that the LangChain agent calls automatically based on user intent:

### 1. `get_company_financials(ticker)`
Live snapshot of key financial metrics from Yahoo Finance: market cap, current price, 52-week range, P/E (trailing & forward), P/B ratio, dividend yield, EPS, revenue TTM, gross profit, EBITDA, total debt, total cash, free cash flow, analyst recommendation, and target mean price.

### 2. `get_price_history(ticker, period)`
Historical OHLCV price data for charting. Period: `1mo` | `3mo` | `6mo` | `1y` | `2y` | `5y`. Interval auto-selected to keep results ≤ 60 rows (daily → weekly → monthly).

### 3. `get_fundamentals(ticker, statement, frequency)`
Full financial statements from Yahoo Finance.
- `statement`: `"income"` | `"balance"` | `"cashflow"`
- `frequency`: `"annual"` (last ~4 fiscal years) | `"quarterly"` (last ~5 quarters)

### 4. `place_order(ticker, side, order_type, qty, notional, …)`
Place a paper-trading order via the **Alpaca Paper API**. Supports market, limit, stop, and stop-limit orders. Accepts quantity (shares) or notional (USD amount). No real money is involved.

### 5. `get_portfolio()`
Current paper-trading portfolio snapshot from Alpaca: account equity, cash, buying power, all open positions (ticker, qty, avg entry price, current price, unrealised P&L), and all open orders.

### 6. `vector_store(params)`
Semantic search over **ChromaDB** financial documents.
- Collection `news_openai`: market sentiment, news headlines, earnings call summaries, analyst commentary, press releases
- Collection `sec_filings_openai`: SEC 10-K annual filings — business descriptions, risk factors, MD&A, audited financials

Supports optional ticker filtering and custom metadata `where`-clauses.

---

## Target Companies

FinsightAI was built and evaluated against the following six large-cap US equities. All RAG ingestion, evaluation golden datasets, and live tool tests use these companies.

| Ticker | Company | Sector |
|---|---|---|
| **AAPL** | Apple Inc. | Technology — Consumer Electronics |
| **MSFT** | Microsoft Corporation | Technology — Cloud & Enterprise Software |
| **GOOGL** | Alphabet Inc. | Technology — Advertising & Cloud |
| **AMZN** | Amazon.com Inc. | Consumer Discretionary — E-commerce & Cloud |
| **NVDA** | NVIDIA Corporation | Technology — Semiconductors / AI Hardware |
| **TSLA** | Tesla Inc. | Consumer Discretionary — Electric Vehicles |

These tickers are stored in a Supabase `public.companies` table and loaded dynamically at ingestion time, so adding or removing a ticker requires no code changes — only a database update.

---

## RAG Ingestion Pipeline

The `RAG-Ingestion/` module populates the four ChromaDB collections queried by the `vector_store` tool. The pipeline is invoked from the CLI:

```bash
python RAG-Ingestion/main.py --mode all           # run both pipelines
python RAG-Ingestion/main.py --mode 10k           # 10-K filings only
python RAG-Ingestion/main.py --mode news          # news only
python RAG-Ingestion/main.py --tickers MSFT TSLA  # filter to specific tickers
```

Every pipeline run writes to **two parallel collections** per data source — one using the lightweight Chroma default embeddings and one using OpenAI `text-embedding-3-small`. This lets the system serve queries even when the OpenAI API is unavailable and enables a direct embedding-quality comparison.

---

### SEC 10-K Pipeline (`RAG-Ingestion/10K/`)

Ingests the most recent annual 10-K filing for each company from the SEC EDGAR database.

| Step | Module | Details |
|---|---|---|
| **Download** | `downloader.py` | Uses `sec-edgar-downloader` to fetch the latest 10-K HTML filing from SEC EDGAR for each ticker. Files are cached under `RAG-Ingestion/data/sec-edgar-filings/<TICKER>/10-K/`. On re-runs, cached files are used directly (no re-download). |
| **Parse** | `parser.py` | Extracts plain text from the primary SEC HTML document (`primary-document.htm`). Strips navigation, scripts, styles, and boilerplate sections to produce clean prose. |
| **Chunk** | `chunker.py` | Applies LangChain `RecursiveCharacterTextSplitter` with **chunk size 1 000 chars** and **200-char overlap**, preserving cross-boundary context for dense financial narrative. |
| **Embed & store** | `embedder.py` / `ingestor.py` | Dual-backend upload: chunks go to `sec_filings_chroma` (Chroma default, `all-MiniLM-L6-v2`) and `sec_filings_openai` (OpenAI `text-embedding-3-small`). Metadata stored per chunk: `ticker`, `company`, `source`, `chunk_index`. |

**Sections covered per 10-K:** Business description, Risk Factors, Management's Discussion & Analysis (MD&A), audited financial statements (income, balance sheet, cash flows), and notes.

---

### Financial News Pipeline (`RAG-Ingestion/News/`)

Ingests recent financial news articles and press releases for each company from Yahoo Finance RSS feeds.

| Step | Module | Details |
|---|---|---|
| **Collect** | `collector.py` | Queries Yahoo Finance news feeds for each ticker and retrieves article metadata (headline, URL, publisher, publish date, UUID). Up to 25 articles per ticker by default. |
| **Scrape** | `scraper.py` | Fetches full article HTML; removes noise tags (`nav`, `footer`, `script`, `aside`); checks relevance by matching ticker or company name in the page title or first 20% of body with ≥ 1 total mention; rejects articles shorter than 400 characters. |
| **Tiering** | `ingestor.py` | Each article is assigned a quality tier based on available content: **high** (full scraped text, ≥ 400 chars), **medium** (Yahoo summary/description, ≥ 60 chars), **low** (synthetic headline document for paywalled articles). |
| **Sentiment** | `sentiment.py` | Runs **ProsusAI/finbert** (FinBERT) on the best available text per article. Outputs `sentiment_label` (`positive` / `negative` / `neutral`) and individual class scores (`sentiment_positive`, `sentiment_negative`, `sentiment_neutral`). Sentiment fields are attached as metadata to every chunk from that article. |
| **Chunk** | `chunker.py` | `RecursiveCharacterTextSplitter` with **chunk size 500 chars** and **100-char overlap** — smaller than 10-K chunks to keep each piece focused on a single news event. |
| **Embed & store** | `ingestor.py` | Same dual-backend pattern: `news_chroma` (default embeddings) and `news_openai` (OpenAI). Idempotent upsert — an article is skipped only when its UUID + ticker combination already exists in **both** collections, so partial failures from a previous run are automatically healed. |

**Metadata stored per news chunk:** `ticker`, `title`, `link`, `publisher`, `published`, `original_uuid`, `quality` (high/medium/low), `sentiment_label`, `sentiment_score`, `sentiment_positive`, `sentiment_negative`, `sentiment_neutral`.

---

## Running the Full Stack with Docker Compose

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24 (or Docker Engine + Compose plugin ≥ 2.20)
- An **OpenAI API key**

### 1 — Create a root `.env` file

```dotenv
# Required
OPENAI_API_KEY=sk-...

# ChromaDB remote instance (required for vector_store tool)
CHROMA_URL=https://<your-chroma-host>
CF-ACCESS-CLIENT-ID=<cloudflare-service-token-id>       # optional
CF-ACCESS-CLIENT-SECRET=<cloudflare-service-token-secret> # optional

# Alpaca Paper Trading (optional – needed for place_order / get_portfolio)
ALPACA_API_KEY=<alpaca-paper-key>
ALPACA_SECRET_KEY=<alpaca-paper-secret>

# LLM configuration (optional – shown with defaults)
LLM_MODEL=openai:gpt-4.1
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
AGENT_MAX_ITERATIONS=10
AGENT_RECURSION_LIMIT=25

# App settings (optional)
APP_NAME="FinsightAI Backend"
ENVIRONMENT=development
DEBUG=false
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
MCP_SERVER_URL=http://localhost:8080/mcp
```

### 2 — Build and start all services

```bash
docker compose up --build
```

> The first build downloads base images and installs all dependencies — allow **3–5 minutes**. Subsequent starts are much faster.

### 3 — Verify services are healthy

```bash
docker compose ps
```

All services should show **healthy** status. You can also check each health endpoint directly:

```bash
curl http://localhost:8080/health   # MCP server
curl http://localhost:8001/health   # Backend
curl http://localhost:3000/health   # Frontend (Nginx)
```

### 4 — Open the app

| URL | What |
|---|---|
| http://localhost:3000/FinInsightAI/ | React frontend |
| http://localhost:8001/docs | Backend Swagger UI |
| http://localhost:8001/redoc | Backend ReDoc |

### Docker Compose Quick-Reference

```bash
docker compose up -d --build          # Start everything (detached)
docker compose logs -f                # Tail all logs
docker compose logs -f backend        # Tail a specific service
docker compose stop                   # Stop (preserves volumes)
docker compose down                   # Remove containers + networks
docker compose down -v                # Full reset (removes volumes too)
docker compose up -d --build backend  # Rebuild a single service
docker compose exec backend bash      # Shell into a container
```

---

## Local Development (without Docker)

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### MCP Server

```bash
cd MCP
pip install -r requirements.txt
MCP_TRANSPORT=http python server.py
# → http://localhost:8080
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
# → http://localhost:8001
```

> Ensure the MCP server is running and `MCP_SERVER_URL` in `.env` points to it before starting the backend.

---

## Backend API Reference

### `POST /api/v1/agent/chat`

Send a message to the financial agent. Returns the full answer once the agent finishes the tool-call loop.

```bash
curl -X POST http://localhost:8001/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key financials for Apple?",
    "conversation_id": "session-1",
    "history": []
  }'
```

### `POST /api/v1/agent/stream`

Same as `/chat` but returns a **Server-Sent Events** stream. Each event is a JSON `StreamChunk`.

```bash
curl -N -X POST http://localhost:8001/api/v1/agent/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare Microsoft and Google revenue"}'
```

Event types: `token` | `tool_start` | `tool_end` | `done` | `error`

### `GET /api/v1/agent/health`

Returns MCP connectivity status and the configured LLM model.

---

## RAG Evaluation Results

The system is evaluated using a hand-crafted **golden dataset of 52 test cases** covering six tickers (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA) across three query categories: SEC 10-K filings, financial news, and live data tools. Evaluation is performed by `tests/rag/test_ragas_evaluation.py` (pytest) and `tests/rag/test_rag.ipynb` (interactive). Results are analysed and visualised in `tests/rag/results/analysis.ipynb`.

Quality thresholds are defined to mirror production acceptance criteria.

---

### Retrieval Quality — Cosine Similarity

Measures whether the retrieved document chunks are semantically close to the query, evaluated on 16 vector-store test cases.

| Embedding Backend | Mean Cosine Similarity | Pass Rate (≥ 0.50) | Threshold |
|---|---|---|---|
| Chroma default (`all-MiniLM-L6-v2`) | 0.617 | **87.5%** (14 / 16) | 0.50 |
| OpenAI `text-embedding-3-small` | 0.619 | **100.0%** (16 / 16) | 0.50 |

The OpenAI embedding backend achieves full pass-rate with a slightly higher mean similarity. The Chroma default backend has two borderline cases (scores of 0.46 and 0.48) that fall below the threshold.

---

### Retrieval Quality — Hit Rate

Measures whether the correct document for each query appears in the top-5 retrieved results (n-results = 5).

| Collection | Embedding Backend | Hit Rate | Threshold |
|---|---|---|---|
| News | Chroma default | **100.0%** (6 / 6) | 70% |
| News | OpenAI | **100.0%** (6 / 6) | 70% |
| SEC 10-K Filings | Chroma default | **90.0%** (9 / 10) | 70% |
| SEC 10-K Filings | OpenAI | **100.0%** (10 / 10) | 70% |

All configurations exceed the 70% threshold. The single SEC Chroma miss is caused by a highly specific capital-expenditure query where the relevant passage is split across chunk boundaries.

---

### RAGAS Generation Quality

Evaluates the quality of answers generated by the full RAG pipeline (retrieval + LLM generation), measured on 16–20 sampled cases using the [RAGAS](https://github.com/explodinggradients/ragas) evaluation framework. RAGAS uses `gpt-4o-mini` as the judge LLM and `text-embedding-3-small` for embedding-based metrics.

| Metric | Score | Threshold | Margin | Status |
|---|---|---|---|---|
| **Faithfulness** | 0.433 | 0.40 | +0.033 | ✅ PASS |
| **Answer Relevancy** | 0.733 | 0.60 | +0.133 | ✅ PASS |

**Faithfulness** (threshold 0.40) measures how factually grounded the generated answer is in the retrieved context (score range 0–1). A score of 0.433 means roughly 43% of claims in generated answers can be directly attributed to retrieved documents. The margin above the threshold is narrow (+0.033), reflecting an expected trade-off in financially-grounded RAG systems where the LLM draws on parametric knowledge to supplement retrieved context — acceptable behaviour for a production financial assistant, but an area for improvement via stricter context-grounding prompts.

**Answer Relevancy** (threshold 0.60) measures how well the answer addresses the question. The score of 0.733 is comfortably above threshold (+0.133). Some answers provide broader financial context than strictly required by the question, which slightly lowers the score but improves usefulness in practice.

---

### Agent Tool Selection Accuracy

Measures whether the LangGraph agent selects the correct MCP tool for each query (n = 20 cases). A score of 1.0 means the correct tool was called; 0.0 means no tool was called or the wrong tool was used.

| Metric | Score | Pass Rate | Threshold | Margin | Status |
|---|---|---|---|---|---|
| **Tool Call Accuracy** | 0.950 | **95.0%** (19 / 20) | 0.80 | +0.150 | ✅ PASS |

The agent correctly routes 19 out of 20 queries to the appropriate tool (+15 pp above the 80% threshold). The one failure involves a query that requires both a live data lookup and a vector-store search simultaneously, which the agent handled with only the live tool.

---

### Agent Response Time

End-to-end latency from query submission to complete answer, measured over 21 test cases with the full stack running.

| Metric | Value |
|---|---|
| **Mean response time** | 7.34 s |
| **Median response time** | ~6.5 s |
| **Min response time** | 3.01 s |
| **Max response time** | 14.99 s |
| **Pass rate** (within time limit) | **95.2%** (20 / 21) |

The single timeout failure occurs on a complex multi-tool query (SEC filings + live data + portfolio lookup) that requires three sequential tool calls. Simple queries (single tool) typically complete in 3–5 seconds.

---

### Evaluation Summary Scorecard

All nine evaluated metrics pass their acceptance thresholds.

| # | Test | Score | Threshold | Margin | Status |
|---|---|---|---|---|---|
| 1 | Similarity pass-rate — Chroma | 87.50% | 50% | +37.50 pp | ✅ PASS |
| 2 | Similarity pass-rate — OpenAI | 100.00% | 50% | +50.00 pp | ✅ PASS |
| 3 | Hit rate — SEC Filings (Chroma) | 90.00% | 70% | +20.00 pp | ✅ PASS |
| 4 | Hit rate — SEC Filings (OpenAI) | 100.00% | 70% | +30.00 pp | ✅ PASS |
| 5 | Hit rate — News (Chroma) | 100.00% | 70% | +30.00 pp | ✅ PASS |
| 6 | Hit rate — News (OpenAI) | 100.00% | 70% | +30.00 pp | ✅ PASS |
| 7 | RAGAS Faithfulness | 43.26% | 40% | +3.26 pp | ✅ PASS |
| 8 | RAGAS Answer Relevancy | 73.33% | 60% | +13.33 pp | ✅ PASS |
| 9 | Tool Call Accuracy | 95.00% | 80% | +15.00 pp | ✅ PASS |

All retrieval metrics (cosine similarity, hit rate) and the tool-routing metric exceed their thresholds by a comfortable margin. The generation-quality metrics (faithfulness, answer relevancy) pass with a narrower margin, which is expected for a domain-specific financial RAG system where the LLM supplements retrieved context with parametric knowledge.

---

## Test Suite

The project uses a six-layer test pyramid. Each layer targets a different scope and runs at a different cost/speed trade-off.

```
tests/
├── unit/              # Pure logic, no I/O — runs in milliseconds
├── integration/       # Wired classes with mocked external services
├── api/               # HTTP contract tests via FastAPI TestClient
├── e2e/               # Full-stack scenarios against a running stack
├── performance/       # Response-time benchmarks
└── rag/               # RAG retrieval + generation quality evaluation
    ├── test_ragas_evaluation.py   # pytest-based evaluation suite
    ├── test_rag.ipynb             # interactive exploratory evaluation
    ├── golden_dataset.json        # 52 curated test cases
    └── results/
        ├── analysis.ipynb         # chart & scorecard notebook
        └── *.xlsx                 # per-run metric exports
```

---

### Unit Tests (`tests/unit/`)

Pure-function tests with no external I/O. All dependencies are mocked. These run in under one second and are the first gate in CI.

| File | What it tests |
|---|---|
| `test_mcp_tools.py` | `_df_to_rows` DataFrame-to-rows conversion; `place_order` input-validation guard (no qty & no notional → error) |
| `test_agent_message_helpers.py` | `_schema_messages_to_lc` (ConversationMessage → LangChain message type) and `_extract_tool_traces` (AIMessage + ToolMessage → ToolCallTrace list) |
| `test_analysis_service_helpers.py` | JSON extraction helpers (`_extract_json_array`, `_extract_json_object`); `_parse_disclosure_insight_cards`; `DisclosureInsightCard` impact-level validator |
| `test_config.py` | Pydantic `Settings` defaults, environment-variable parsing, and field validators |
| `test_finbert_sentiment.py` | `FinBERTSentiment.analyse` label selection, score calculation, and output shape — model is mocked to avoid downloading 400 MB in CI |
| `test_news_chunker.py` | `NewsChunker` chunk count, overlap, metadata propagation, and edge-cases (empty text, text shorter than chunk size) |

---

### Integration Tests (`tests/integration/`)

Wire together real class instances but mock all external services (OpenAI, ChromaDB, Supabase, HTTP). These verify that the internal plumbing of each service is correct end-to-end.

| File | What it tests |
|---|---|
| `test_agent_service.py` | `AgentService.chat` full request–response cycle with mocked LLM and MCP; message history propagation; tool-trace extraction |
| `test_analysis_service.py` | `AnalysisService` JSON parsing and schema mapping for every analysis endpoint (AI themes, disclosure insights, filing risks, market news, overall outlook, sentiment divergence) |
| `test_news_ingestor.py` | `NewsIngestor.ingest` orchestration: discover → scrape → chunk → sentiment → Chroma upload; idempotency (skip-if-seen guard); per-tier (high/medium/low) routing |

---

### API Tests (`tests/api/`)

HTTP contract tests using FastAPI's `TestClient`. All LLM, MCP, and database calls are mocked via the root `conftest.py`. These ensure the API surface stays stable.

| File | What it tests |
|---|---|
| `test_agent_endpoints.py` | `POST /api/v1/agent/chat` — status codes, response schema, SSE streaming events (`token`, `tool_start`, `tool_end`, `done`, `error`), validation errors (missing/empty messages) |
| `test_analysis_endpoints.py` | `POST /api/v1/analysis/*` — all six analysis endpoints; expected response schema fields; error handling when the agent call fails |

---

### End-to-End Tests (`tests/e2e/`)

Full-stack tests that run against the actual Docker Compose stack (`BACKEND_URL`, `CHROMA_URL` must be set). These are excluded from CI and run manually before a release.

Scenarios covered: a user submitting a sequence of financial queries across different tools (price history → fundamentals → news → RAG → portfolio); multi-turn conversation with context retention; graceful error handling when a tool returns no data.

---

### Performance Tests (`tests/performance/`)

Benchmarks for critical paths:

| Benchmark | Description | Threshold |
|---|---|---|
| **Agent response time** | End-to-end latency for a single-tool query | < 10 s |
| **RAG retrieval latency** | ChromaDB `query()` call with `n_results=5` | < 2 s |
| **Batch embedding throughput** | Chunks per second during ingestion | > 10 chunks/s |

---

### RAG Evaluation Tests (`tests/rag/`)

The most comprehensive test suite — evaluates the full retrieval-augmented generation pipeline across all six tickers using a 52-case golden dataset. Marked `@pytest.mark.live` and `@pytest.mark.rag`; require live ChromaDB and backend instances.

#### Golden Dataset (`golden_dataset.json`)

52 hand-crafted questions spanning all six tickers and all six MCP tools:

| Expected Tool | Cases | Example question |
|---|---|---|
| `vector_store` | 16 | "What are Amazon's main risk factors according to the 10-K?" |
| `get_fundamentals` | 9 | "What was Apple's total revenue in fiscal year 2024?" |
| `get_company_financials` | 9 | "What is NVIDIA's current market capitalisation and P/E ratio?" |
| `place_order` | 7 | "Buy 10 shares of Apple at market price" |
| `get_price_history` | 6 | "Show me Apple's historical stock price for the last year" |
| `get_portfolio` | 5 | "What is my current portfolio balance?" |

Each case includes: `id`, `question`, `ticker`, `expected_tool`, `expected_collection` (for RAG cases), `expected_keywords`, and `ground_truth` answer.

#### Test Classes and Metrics

| Test class | Marker | Metric | How it works |
|---|---|---|---|
| `TestRetrievalQualityChroma` | `live`, `rag` | **Cosine similarity** | Queries `sec_filings_chroma` and `news_chroma` with Chroma default embeddings; computes `1 − distance` for the top-1 result; asserts ≥ 0.50 per case. **Hit rate** also checked: top-5 results must contain at least one chunk with an expected keyword; asserts hit rate ≥ 70%. |
| `TestRetrievalQualityOpenAI` | `live`, `rag` | **Cosine similarity + hit rate** | Same as above but against the `_openai` collections using `text-embedding-3-small`. |
| `TestRAGASEvaluation` | `live`, `rag` | **Faithfulness** | Calls the agent, collects retrieved context, evaluates with RAGAS `faithfulness` metric (LLM-as-judge: is each claim in the answer grounded in the retrieved context?). Judge model: `gpt-4o-mini`. Embedding model: `text-embedding-3-small`. Threshold: ≥ 0.40. |
| `TestRAGASEvaluation` | `live`, `rag` | **Answer Relevancy** | RAGAS `answer_relevancy` — embeds generated questions back and checks alignment with the original query. Embedding model: `text-embedding-3-small`. Threshold: ≥ 0.60. |
| `TestRAGASEvaluation` | `live`, `rag` | **Context Recall** | RAGAS `context_recall` — checks whether the ground-truth information could be found in the retrieved context. Threshold: ≥ 0.70. |
| `TestRAGASEvaluation` | `live`, `rag` | **Tool Call Accuracy** | Calls the agent for every RAG-annotated case; checks whether `expected_tool` (e.g. `get_news`, `search_sec_filings`) appears in the list of tool names called. Threshold: ≥ 0.80. |
| `TestRAGASEvaluation` | `live`, `rag` | **Response Time** | Records wall-clock latency for each agent call and exports to `response_time_<date>.xlsx` for analysis in the notebook. |

Results for every test run are saved as date-stamped `.xlsx` files in `tests/rag/results/` and consumed by `analysis.ipynb` for visualisation.

---

**Run all tests:**
```bash
uv run pytest
```

**Run a specific layer:**
```bash
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/api/
uv run pytest -m "live and rag" tests/rag/test_ragas_evaluation.py -v
```

**Generate RAG result files and open the analysis notebook:**
```bash
uv run pytest -m "live and rag" tests/rag/test_ragas_evaluation.py
jupyter lab tests/rag/results/analysis.ipynb
```

CI runs the unit, integration, and API tests on every push via [`.github/workflows/tests.yml`](.github/workflows/tests.yml). The `live` and `rag` marked tests require a running stack and are run manually.

---

## Deployment

The **frontend** is automatically built and deployed to **GitHub Pages** on every push or merge to `main` via the [deploy workflow](.github/workflows/deploy.yml).

For **full-stack deployment**, run `docker compose up -d --build` on any Linux host with Docker installed, then expose ports 3000 (frontend) and 8001 (backend API) through your load balancer or reverse proxy. Ensure the `CHROMA_URL` environment variable points to your ChromaDB instance and the `OPENAI_API_KEY` is set.

---

## License

MIT
