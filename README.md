# FinsightAI

An AI-powered financial insights platform that combines a React frontend, a FastAPI LangGraph agent backend, a FastMCP tool server, and a ChromaDB vector store into a single Dockerised stack.

**Live demo (frontend only):** [https://utsnlpgroup.github.io/FinInsightAI/](https://utsnlpgroup.github.io/FinInsightAI/)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker network                        │
│                                                              │
│  ┌──────────┐    HTTP     ┌──────────┐    HTTP     ┌──────┐  │
│  │ frontend │ ──────────► │ backend  │ ──────────► │ MCP  │  │
│  │  :3000   │            │  :8001   │            │ :8080 │  │
│  │  Nginx   │            │ FastAPI  │            │FastMCP│  │
│  └──────────┘            │LangGraph │            └───┬───┘  │
│                          └──────────┘                │      │
│                                                      │      │
│                                              ┌───────▼────┐ │
│                                              │  ChromaDB  │ │
│                                              │   :8000    │ │
│                                              └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

| Service | Technology | Host port |
|---|---|---|
| `frontend` | React 19 + Vite + Tailwind CSS, served by Nginx | **3000** |
| `backend` | FastAPI + LangGraph ReAct agent | **8001** |
| `mcp-server` | FastMCP (Yahoo Finance + ChromaDB tools) | **8080** |
| `chromadb` | ChromaDB vector store | **8000** |

Startup order enforced by health-check dependencies:

```
chromadb → mcp-server → backend → frontend
```

---

## Project Structure

```
finsightAI/
├── frontend/                  # React + TypeScript + Vite SPA
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── backend/                   # FastAPI + LangGraph agent
│   ├── app/
│   │   ├── main.py            # App factory + lifespan
│   │   ├── core/              # Config + DI dependencies
│   │   ├── agents/            # LangGraph ReAct graph
│   │   ├── services/          # AgentService + MCPClientManager
│   │   ├── schemas/           # Pydantic request/response models
│   │   └── api/v1/            # REST endpoints
│   ├── Dockerfile
│   └── requirements.txt
│
├── MCP/                       # FastMCP tool server
│   ├── server.py              # get_company_financials + vector_store tools
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml         # Full-stack orchestration
└── README.md
```

---

## Running the Full Stack with Docker Compose

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24 (or Docker Engine + Compose plugin ≥ 2.20)
- An **OpenAI API key** (or Anthropic key if you prefer Claude)

### 1 — Create a root `.env` file

```bash
cp backend/.env.example .env   # start from the backend template
```

Then open `.env` and set at minimum:

```dotenv
OPENAI_API_KEY=sk-...          # required for the LangGraph agent
# or
ANTHROPIC_API_KEY=sk-ant-...   # if you prefer claude, also set LLM_MODEL below

LLM_MODEL=openai:gpt-4.1       # default – change to e.g. anthropic:claude-opus-4-5
```

All other values have sensible defaults and do not need to be changed for a local run.

### 2 — Build and start all services

```bash
docker compose up --build
```

> The first build downloads base images and installs all dependencies.
> Allow **3–5 minutes** on the first run. Subsequent starts are much faster.

### 3 — Verify services are healthy

```bash
docker compose ps
```

All four services should show **healthy** status. You can also hit each health endpoint:

```bash
curl http://localhost:8000/api/v1/heartbeat   # ChromaDB
curl http://localhost:8080/health             # MCP server
curl http://localhost:8001/health             # Backend
curl http://localhost:3000/health             # Frontend (Nginx)
```

### 4 — Open the app

| URL | What |
|---|---|
| http://localhost:3000/FinInsightAI/ | React frontend |
| http://localhost:8001/docs | Backend Swagger UI |
| http://localhost:8001/redoc | Backend ReDoc |

---

## Docker Compose Quick-Reference

```bash
# Start everything (detached)
docker compose up -d --build

# Tail logs for all services
docker compose logs -f

# Tail logs for a specific service
docker compose logs -f backend

# Stop all services (preserves volumes)
docker compose stop

# Stop and remove containers + networks (preserves volumes)
docker compose down

# Stop and remove containers, networks, AND volumes (full reset)
docker compose down -v

# Rebuild a single service without restarting the others
docker compose up -d --build backend

# Open a shell inside a running container
docker compose exec backend bash
docker compose exec mcp-server bash
```

---

## Local Development (without Docker)

Run each service individually for a faster edit–reload cycle.

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
cp .env.example .env   # edit as needed
python server.py
# → stdio by default; set MCP_TRANSPORT=http for HTTP mode
```

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY and MCP_SERVER_URL
uvicorn app.main:app --reload --port 8001
# → http://localhost:8001
```

> Make sure the MCP server is running and `MCP_SERVER_URL` in `.env` points to it before starting the backend.

---

## Backend API

### `POST /api/v1/agent/chat`

Send a message to the financial agent. Returns the full answer once the agent finishes reasoning.

```bash
curl -X POST http://localhost:8001/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key financials for Apple?",
    "conversation_id": "my-session-1",
    "history": []
  }'
```

### `POST /api/v1/agent/stream`

Same as `/chat` but returns a **Server-Sent Events** stream. Each line is a JSON `StreamChunk`:

```bash
curl -N -X POST http://localhost:8001/api/v1/agent/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare Microsoft and Google revenue"}'
```

Event types: `token` | `tool_start` | `tool_end` | `done` | `error`

### `GET /api/v1/agent/health`

Returns MCP connectivity status and configured LLM model.

---

## MCP Tools

The MCP server exposes two tools available to the LangGraph agent:

### `get_company_financials(ticker)`
Fetches live data from **Yahoo Finance**: market cap, price, P/E ratio, EPS, revenue, EBITDA, free cash flow, analyst recommendation, and more.

### `vector_store(params)`
Bidirectional interface to **ChromaDB**:
- `operation="add"` — embed and persist financial documents with metadata
- `operation="query"` — semantic similarity search over stored documents

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Frontend server | Nginx 1.27 |
| Backend framework | FastAPI, Uvicorn |
| AI agent | LangGraph (ReAct), LangChain |
| MCP integration | langchain-mcp-adapters, FastMCP |
| LLM | OpenAI GPT-4.1 (default) / Anthropic Claude |
| Vector store | ChromaDB |
| Financial data | yfinance (Yahoo Finance) |
| Containerisation | Docker, Docker Compose |
| CI / CD | GitHub Actions → GitHub Pages (frontend) |

---

## Deployment

The frontend is automatically deployed to **GitHub Pages** on every push or merge to `main` via the [deploy workflow](.github/workflows/deploy.yml).

For full-stack deployment, point `docker compose up` at any Linux host with Docker installed and expose ports 3000 and 8001 through your load balancer or reverse proxy.

---

## License

MIT
