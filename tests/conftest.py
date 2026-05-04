"""
Root conftest – shared pytest fixtures for all test suites.

Path strategy:
  pyproject.toml sets pythonpath = ["backend", "RAG-Ingestion"] so imports
  resolve as:
    from app.main import create_app          (backend/app/main.py)
    from News.chunker import NewsChunker     (RAG-Ingestion/News/chunker.py)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load test environment variables before any test collection happens.
# tests/.env.test holds real credentials for live/RAG tests so you never
# need to manually `export` them in the shell.
load_dotenv(Path(__file__).parent / ".env", override=False)

# ── FastAPI / backend imports ─────────────────────────────────────────────────

from app.core.config import Settings
from app.core.dependencies import (
    get_agent_service,
    get_analysis_service,
    get_chat_service,
    get_mcp_manager,
)
from app.main import create_app
from app.schemas.agent import (
    ChatRequest,
    ChatResponse,
    StreamChunk,
    StreamEventType,
    ToolCallTrace,
)
from app.schemas.analysis import (
    AIThemesResponse,
    DisclosureInsightCard,
    DisclosureInsightsResponse,
    FilingRisk,
    FilingRisksResponse,
    MarketNewsItem,
    MarketNewsResponse,
    OverallOutlookResponse,
    SentimentBreakdown,
    SentimentDivergenceResponse,
)
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionSummary,
    ChatSessionUpdate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_test_settings(**overrides) -> Settings:
    """Return a Settings object safe for unit/integration tests (no real creds)."""
    defaults = dict(
        app_name="FinsightAI Test",
        environment="development",
        openai_api_key="sk-test-00000000000000000000000000000000",
        supabase_db_url="postgresql://test:test@localhost:5432/testdb",
        mcp_server_url="http://localhost:8080/mcp",
        llm_model="openai:gpt-5.4-mini",
        llm_temperature=0.0,
        llm_max_tokens=512,
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ── Mock factories ────────────────────────────────────────────────────────────

def _make_mock_mcp_manager() -> MagicMock:
    manager = MagicMock()
    manager.is_connected = True
    manager.get_tools.return_value = []
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    return manager


def _make_mock_agent_service(answer: str = "Apple's revenue was $391B in FY2024.") -> AsyncMock:
    svc = AsyncMock()
    svc.chat.return_value = ChatResponse(
        conversation_id="test-conv-id",
        answer=answer,
        tool_calls=[
            ToolCallTrace(
                tool_name="vector_store",
                input={"collection_name": "sec_filings", "query_text": "revenue"},
                output="Retrieved 3 documents",
            )
        ],
        input_tokens=120,
        output_tokens=80,
    )

    async def _mock_stream(*args, **kwargs) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(event=StreamEventType.TOOL_START, data={"tool": "vector_store", "input": {}}, conversation_id="test-conv-id")
        yield StreamChunk(event=StreamEventType.TOKEN, data="Apple", conversation_id="test-conv-id")
        yield StreamChunk(event=StreamEventType.TOKEN, data=" revenue", conversation_id="test-conv-id")
        yield StreamChunk(event=StreamEventType.TOOL_END, data={"tool": "vector_store", "output": "3 docs"}, conversation_id="test-conv-id")
        yield StreamChunk(event=StreamEventType.DONE, data={"conversation_id": "test-conv-id"}, conversation_id="test-conv-id")

    svc.stream = _mock_stream
    return svc


def _make_mock_analysis_service() -> AsyncMock:
    svc = AsyncMock()

    svc.get_overall_outlook.return_value = OverallOutlookResponse(
        ticker="AAPL",
        outlook="While Apple highlights robust services growth in their 10-K, external sentiment remains cautious.",
        tags=["Services Growth", "AI Integration", "Regulatory Risk"],
        tool_calls=[],
    )
    svc.get_filing_risks.return_value = FilingRisksResponse(
        ticker="AAPL",
        risks=[
            FilingRisk(title="Regulatory Scrutiny", description="Ongoing antitrust investigations.", category="Regulatory"),
            FilingRisk(title="Supply Chain Risk", description="Concentration in Asia manufacturing.", category="Operational"),
        ],
        tool_calls=[],
    )
    svc.get_risk_insights.return_value = DisclosureInsightsResponse(
        ticker="AAPL",
        cards=[
            DisclosureInsightCard(
                title="Regulatory Scrutiny",
                page_ref="10-K · Item 1A",
                description="Ongoing antitrust investigations.",
                impact="HIGH IMPACT",
                impact_level="high",
                icon="⚠️",
            )
        ],
        tool_calls=[],
    )
    svc.get_growth_strategy_insights.return_value = DisclosureInsightsResponse(
        ticker="AAPL",
        cards=[
            DisclosureInsightCard(
                title="Services Expansion",
                page_ref="MD&A",
                description="Apple TV+ and App Store driving recurring revenue.",
                impact="STRATEGIC DRIVER",
                impact_level="positive_high",
                icon="📈",
            )
        ],
        tool_calls=[],
    )
    svc.get_capex_insights.return_value = DisclosureInsightsResponse(
        ticker="AAPL",
        cards=[
            DisclosureInsightCard(
                title="Data Centre Investment",
                page_ref="Item 7",
                description="$11B in capital expenditures for cloud infrastructure.",
                impact="HIGH IMPACT",
                impact_level="high",
                icon="🏗️",
            )
        ],
        tool_calls=[],
    )
    svc.get_ai_themes.return_value = AIThemesResponse(
        ticker="AAPL",
        themes=["AI Integration", "Services Growth", "Vision Pro Launch"],
        tool_calls=[],
    )
    svc.get_sentiment_divergence.return_value = SentimentDivergenceResponse(
        ticker="AAPL",
        breakdown=[
            SentimentBreakdown(label="Bullish", percentage=60, sentiment="bullish"),
            SentimentBreakdown(label="Neutral", percentage=30, sentiment="neutral"),
            SentimentBreakdown(label="Bearish", percentage=10, sentiment="bearish"),
        ],
        tool_calls=[],
    )
    svc.get_market_news.return_value = MarketNewsResponse(
        ticker="AAPL",
        items=[
            MarketNewsItem(
                title="Apple Reports Record Q4 Earnings",
                summary="Apple exceeded analyst expectations with strong iPhone sales.",
                sentiment="bullish",
                source="BLOOMBERG",
                time_ago="2H AGO",
            )
        ],
        tool_calls=[],
    )
    return svc


def _make_mock_chat_service() -> AsyncMock:
    import uuid
    from datetime import datetime, timezone

    svc = AsyncMock()
    _now = datetime.now(tz=timezone.utc)
    _uid = uuid.uuid4()
    _sid = uuid.uuid4()

    _session = ChatSessionResponse(
        id=_sid,
        user_id=_uid,
        title="Test Chat",
        messages=[],
        created_at=_now,
        updated_at=_now,
    )
    _summary = ChatSessionSummary(
        id=_sid,
        user_id=_uid,
        title="Test Chat",
        created_at=_now,
        updated_at=_now,
    )

    svc.create_session.return_value = _session
    svc.list_sessions.return_value = [_summary]
    svc.get_session.return_value = _session
    svc.update_session.return_value = _session
    svc.delete_session.return_value = True
    return svc


# ── Shared pytest fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test Settings singleton reused across the entire test session."""
    return _make_test_settings()


@pytest.fixture
def mock_mcp_manager() -> MagicMock:
    return _make_mock_mcp_manager()


@pytest.fixture
def mock_agent_service() -> AsyncMock:
    return _make_mock_agent_service()


@pytest.fixture
def mock_analysis_service() -> AsyncMock:
    return _make_mock_analysis_service()


@pytest.fixture
def mock_chat_service() -> AsyncMock:
    return _make_mock_chat_service()


@pytest.fixture
def test_app(
    test_settings: Settings,
    mock_mcp_manager: MagicMock,
    mock_agent_service: AsyncMock,
    mock_analysis_service: AsyncMock,
    mock_chat_service: AsyncMock,
):
    """
    FastAPI test application with all external dependencies mocked.

    - MCP manager → stubbed (no real connection)
    - AgentService → AsyncMock returning canned ChatResponse
    - AnalysisService → AsyncMock returning canned analysis responses
    - ChatService → AsyncMock returning canned CRUD responses
    - DB pool (close_pool) → no-op
    """
    with (
        patch("app.main.MCPClientManager", return_value=mock_mcp_manager),
        patch("app.core.database.close_pool", new_callable=AsyncMock),
    ):
        application = create_app(test_settings)

    application.state.mcp_manager = mock_mcp_manager

    application.dependency_overrides[get_mcp_manager] = lambda: mock_mcp_manager
    application.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    application.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service
    application.dependency_overrides[get_chat_service] = lambda: mock_chat_service

    yield application

    application.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Sync TestClient for the mocked FastAPI app."""
    from fastapi.testclient import TestClient
    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c
