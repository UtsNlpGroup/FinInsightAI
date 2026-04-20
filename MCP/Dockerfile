# ──────────────────────────────────────────────────────────────────────────────
# FinsightAI MCP Server
# Runs FastMCP over HTTP so other containers (and external clients) can reach it.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Keeps Python from generating .pyc files and enables real-time log output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# sentence-transformers needs these native libs for tokenisation
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ──────────────────────────────────────────────────────────────────────────────
# Install Python dependencies (cached layer – only rebuilt when requirements change)
# ──────────────────────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Copy application source
# ──────────────────────────────────────────────────────────────────────────────
COPY server.py .

# Persistent ChromaDB data lives in a named volume mounted at /data/chroma
ENV CHROMA_PERSIST_DIR=/data/chroma \
    MCP_TRANSPORT=http \
    MCP_PORT=8080

EXPOSE 8080

# Lightweight health-check – FastMCP exposes /health on the HTTP transport
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "server.py"]
