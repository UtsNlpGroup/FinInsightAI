# FinsightAI MCP Server

A [FastMCP](https://gofastmcp.com) server that exposes two financial AI tools to any MCP-compatible LLM client (Claude Desktop, Cursor, etc.).

## Tools

### 1. `get_company_financials`
Fetches live financial data for any US-listed company via **Yahoo Finance**.

| Field returned | Description |
|---|---|
| `ticker` / `company_name` | Symbol and full name |
| `sector` / `industry` | GICS classification |
| `market_cap`, `currency` | Size and denomination |
| `current_price`, `previous_close` | Latest price data |
| `52w_high` / `52w_low` | Range |
| `pe_ratio`, `forward_pe`, `price_to_book` | Valuation multiples |
| `dividend_yield`, `eps` | Income metrics |
| `revenue_ttm`, `gross_profit`, `ebitda` | Profitability |
| `total_debt`, `total_cash`, `free_cashflow` | Balance sheet |
| `analyst_recommendation`, `target_mean_price` | Consensus view |
| `description` | Business summary |

**Example call (via LLM):**
> "Get the financials for Apple."  
> → calls `get_company_financials(ticker="AAPL")`

---

### 2. `vector_store`
Bidirectional interface to a **ChromaDB** collection for storing and semantically searching financial documents.

#### `add` operation
Embeds and persists documents into the named collection.

```json
{
  "operation": "add",
  "collection_name": "financial_docs",
  "documents": ["Apple reported Q1 revenue of $119.6B..."],
  "ids": ["aapl-q1-2025"],
  "metadatas": [{"ticker": "AAPL", "source": "earnings_report", "date": "2025-02-01"}]
}
```

#### `query` operation
Semantic similarity search against stored documents.

```json
{
  "operation": "query",
  "collection_name": "financial_docs",
  "query_text": "Apple revenue growth 2025",
  "n_results": 5,
  "where": {"ticker": "AAPL"}
}
```

---

## Setup

### 1. Install dependencies

```bash
cd MCP
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `CHROMA_HOST` | *(empty)* | Set to connect to a remote ChromaDB server; leave empty for local persistent storage |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Local storage path when using persistent client |
| `OPENAI_API_KEY` | *(empty)* | Enables OpenAI `text-embedding-3-small`; omit to use the free built-in model |
| `MCP_TRANSPORT` | `stdio` | `stdio` for local clients, `http` for remote |
| `MCP_PORT` | `8080` | HTTP port (only used when `MCP_TRANSPORT=http`) |

### 3. Run the server

**stdio (default – for Claude Desktop / Cursor):**
```bash
python server.py
```

**HTTP transport:**
```bash
MCP_TRANSPORT=http python server.py
# or
fastmcp run server.py:mcp --transport http --port 8080
```

---

## Connecting to Claude Desktop

Add this block to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "finsight": {
      "command": "python",
      "args": ["/absolute/path/to/MCP/server.py"],
      "env": {
        "CHROMA_PERSIST_DIR": "/absolute/path/to/MCP/chroma_data"
      }
    }
  }
}
```

---

## Project Structure

```
MCP/
├── server.py          # FastMCP server + tool definitions
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
├── .env               # Your local config (git-ignored)
└── chroma_data/       # Auto-created ChromaDB persistent storage
```
