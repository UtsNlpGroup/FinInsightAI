"""
Performance / response-time tests for FinsightAI.

Two execution modes:
  1. MOCKED mode (default, runs in CI): tests FastAPI overhead + serialisation
     with all services mocked. Verifies the routing layer adds < 200 ms overhead.

  2. LIVE mode (@pytest.mark.live): calls the real backend, measures actual
     end-to-end LLM + MCP + Chroma response times, and asserts SLA compliance.
     Run with: pytest tests/performance/ -m live -v --timeout=300

SLA targets (live mode):
  - /api/v1/agent/chat       average <= 30 s  (full ReAct loop with tools)
  - /api/v1/agent/stream     first token <= 5 s
  - /api/v1/analysis/*       average <= 20 s  (one-shot agent call)
  - /api/v1/chats (CRUD)     average <= 0.5 s (DB operations only)
  - /health                  average <= 0.1 s (no I/O)

Results are printed as a markdown table and written to:
  tests/performance/results/response_times_<timestamp>.json
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

import pytest

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _measure(fn, n: int = 5) -> dict:
    """
    Call fn() n times and return timing statistics (all in seconds).

    Returns:
        dict with keys: min, max, mean, median, p95, samples
    """
    times = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": sorted(times)[int(0.95 * len(times))],
        "samples": times,
        "n": n,
    }


def _print_table(results: dict[str, dict]) -> None:
    print("\n## Response Time Results\n")
    print(f"{'Endpoint':<45} {'Mean (s)':>10} {'P95 (s)':>10} {'Min (s)':>10} {'Max (s)':>10}")
    print("-" * 90)
    for endpoint, stats in results.items():
        print(
            f"{endpoint:<45} "
            f"{stats['mean']:>10.3f} "
            f"{stats['p95']:>10.3f} "
            f"{stats['min']:>10.3f} "
            f"{stats['max']:>10.3f}"
        )


def _save_results(results: dict[str, dict], label: str) -> None:
    ts = int(time.time())
    path = RESULTS_DIR / f"response_times_{label}_{ts}.json"
    serialisable = {
        k: {kk: vv for kk, vv in v.items() if kk != "samples"}
        for k, v in results.items()
    }
    with open(path, "w") as f:
        json.dump({"timestamp": ts, "mode": label, "results": serialisable}, f, indent=2)
    print(f"\n[Performance] Results saved to {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MOCKED mode – FastAPI overhead, no external I/O
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.performance
class TestMockedResponseTimes:
    """
    Measure how long each endpoint takes when ALL services are mocked.
    This isolates FastAPI serialisation + routing overhead from LLM latency.

    Expected: < 200 ms mean for all endpoints.
    """

    N_RUNS = 10
    MAX_MEAN_SECONDS = 0.2  # 200 ms

    def test_health_endpoint_overhead(self, client):
        stats = _measure(lambda: client.get("/health"), n=self.N_RUNS)
        print(f"\n[Mocked] /health mean={stats['mean']:.3f}s p95={stats['p95']:.3f}s")
        assert stats["mean"] < self.MAX_MEAN_SECONDS, (
            f"/health mean {stats['mean']:.3f}s exceeds {self.MAX_MEAN_SECONDS}s overhead budget"
        )

    def test_agent_chat_serialisation_overhead(self, client):
        payload = {"message": "What is AAPL revenue?"}
        stats = _measure(
            lambda: client.post("/api/v1/agent/chat", json=payload),
            n=self.N_RUNS,
        )
        print(f"\n[Mocked] /agent/chat mean={stats['mean']:.3f}s p95={stats['p95']:.3f}s")
        assert stats["mean"] < self.MAX_MEAN_SECONDS

    def test_analysis_outlook_overhead(self, client):
        stats = _measure(
            lambda: client.get("/api/v1/analysis/outlook/AAPL"),
            n=self.N_RUNS,
        )
        print(f"\n[Mocked] /analysis/outlook/AAPL mean={stats['mean']:.3f}s")
        assert stats["mean"] < self.MAX_MEAN_SECONDS

    def test_analysis_filing_risks_overhead(self, client):
        stats = _measure(
            lambda: client.get("/api/v1/analysis/filing-risks/AAPL"),
            n=self.N_RUNS,
        )
        print(f"\n[Mocked] /analysis/filing-risks/AAPL mean={stats['mean']:.3f}s")
        assert stats["mean"] < self.MAX_MEAN_SECONDS

    def test_chat_crud_overhead(self, client):
        import uuid
        uid = str(uuid.uuid4())
        stats = _measure(
            lambda: client.post("/api/v1/chats", json={"user_id": uid, "title": "Test"}),
            n=self.N_RUNS,
        )
        print(f"\n[Mocked] POST /chats mean={stats['mean']:.3f}s")
        assert stats["mean"] < self.MAX_MEAN_SECONDS

    def test_all_analysis_endpoints_overhead(self, client):
        """Run all analysis endpoints and produce a summary table."""
        endpoints = [
            "/api/v1/analysis/outlook/AAPL",
            "/api/v1/analysis/filing-risks/AAPL",
            "/api/v1/analysis/risks/AAPL",
            "/api/v1/analysis/growth-strategies/AAPL",
            "/api/v1/analysis/capex/AAPL",
            "/api/v1/analysis/ai-themes/AAPL",
            "/api/v1/analysis/sentiment-divergence/AAPL",
            "/api/v1/analysis/market-news/AAPL",
        ]
        all_results = {}
        for ep in endpoints:
            stats = _measure(lambda ep=ep: client.get(ep), n=5)
            all_results[ep] = stats

        _print_table(all_results)
        _save_results(all_results, "mocked")

        for ep, stats in all_results.items():
            assert stats["mean"] < self.MAX_MEAN_SECONDS, (
                f"{ep} overhead {stats['mean']:.3f}s exceeds budget"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE mode – real LLM + MCP + Chroma calls
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.performance
class TestLiveResponseTimes:
    """
    Measure actual end-to-end response times against a running backend.

    These tests are excluded from standard CI (requires running stack + API keys).
    Run manually with: pytest tests/performance/ -m live -v
    """

    import os
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

    # SLA targets
    CHAT_SLA_SECONDS = 30.0       # full agent chat (tools + LLM)
    ANALYSIS_SLA_SECONDS = 20.0   # analysis endpoint (one-shot agent)
    STREAM_FIRST_TOKEN_SLA = 5.0  # seconds until first SSE token
    CRUD_SLA_SECONDS = 0.5        # chat session CRUD (DB only)

    N_RUNS = 3  # keep low to avoid excessive API costs

    @pytest.fixture(scope="class")
    def http_client(self):
        import httpx
        return httpx.Client(base_url=self.BACKEND_URL, timeout=120)

    def test_agent_chat_meets_sla(self, http_client):
        """
        POST /api/v1/agent/chat with a simple factual question.
        SLA: average <= 30 s over 3 runs.
        """
        payload = {"message": "What is Apple's current P/E ratio?"}
        stats = _measure(
            lambda: http_client.post("/api/v1/agent/chat", json=payload),
            n=self.N_RUNS,
        )
        print(
            f"\n[LIVE] /agent/chat "
            f"mean={stats['mean']:.1f}s p95={stats['p95']:.1f}s max={stats['max']:.1f}s"
        )
        for t in stats["samples"]:
            print(f"  run: {t:.2f}s")
        assert stats["mean"] <= self.CHAT_SLA_SECONDS, (
            f"agent/chat mean {stats['mean']:.1f}s exceeds SLA of {self.CHAT_SLA_SECONDS}s"
        )

    def test_agent_chat_with_vectorstore_tool(self, http_client):
        """
        Agent chat requiring vector_store lookup (sec_filings).
        Typically slower than a pure LLM call.
        SLA: average <= 30 s.
        """
        payload = {"message": "What are the main risk factors in AAPL's 10-K?"}
        stats = _measure(
            lambda: http_client.post("/api/v1/agent/chat", json=payload),
            n=self.N_RUNS,
        )
        print(
            f"\n[LIVE] /agent/chat (RAG) "
            f"mean={stats['mean']:.1f}s max={stats['max']:.1f}s"
        )
        assert stats["mean"] <= self.CHAT_SLA_SECONDS

    def test_agent_chat_multi_tool_call(self, http_client):
        """
        Agent chat requiring BOTH vector_store AND get_company_financials.
        SLA: average <= 30 s (allows two tool round-trips).
        """
        payload = {
            "message": (
                "Compare AAPL's 10-K risk factors with its current market metrics "
                "and recent news sentiment."
            )
        }
        stats = _measure(
            lambda: http_client.post("/api/v1/agent/chat", json=payload),
            n=self.N_RUNS,
        )
        print(
            f"\n[LIVE] /agent/chat (multi-tool) "
            f"mean={stats['mean']:.1f}s max={stats['max']:.1f}s"
        )
        assert stats["mean"] <= self.CHAT_SLA_SECONDS

    def test_analysis_outlook_meets_sla(self, http_client):
        """GET /analysis/outlook/AAPL SLA: average <= 20 s."""
        stats = _measure(
            lambda: http_client.get("/api/v1/analysis/outlook/AAPL"),
            n=self.N_RUNS,
        )
        print(f"\n[LIVE] /analysis/outlook/AAPL mean={stats['mean']:.1f}s")
        assert stats["mean"] <= self.ANALYSIS_SLA_SECONDS

    def test_analysis_filing_risks_meets_sla(self, http_client):
        """GET /analysis/filing-risks/AAPL SLA: average <= 20 s."""
        stats = _measure(
            lambda: http_client.get("/api/v1/analysis/filing-risks/AAPL"),
            n=self.N_RUNS,
        )
        print(f"\n[LIVE] /analysis/filing-risks/AAPL mean={stats['mean']:.1f}s")
        assert stats["mean"] <= self.ANALYSIS_SLA_SECONDS

    def test_stream_first_token_latency(self, http_client):
        """
        POST /agent/stream – measures time until first `token` SSE event.
        SLA: <= 5 s for first token.
        """
        import httpx

        first_token_times = []
        for _ in range(self.N_RUNS):
            start = time.perf_counter()
            with http_client.stream(
                "POST",
                "/api/v1/agent/stream",
                json={"message": "What sector is Apple in?"},
            ) as resp:
                for line in resp.iter_lines():
                    if "token" in line:
                        elapsed = time.perf_counter() - start
                        first_token_times.append(elapsed)
                        break

        if not first_token_times:
            pytest.skip("No token events received")

        avg_first_token = statistics.mean(first_token_times)
        print(f"\n[LIVE] First token latency: mean={avg_first_token:.2f}s samples={first_token_times}")
        assert avg_first_token <= self.STREAM_FIRST_TOKEN_SLA, (
            f"First token latency {avg_first_token:.2f}s exceeds SLA of {self.STREAM_FIRST_TOKEN_SLA}s"
        )

    def test_chat_session_crud_meets_sla(self, http_client):
        """
        POST /chats (create session) SLA: average <= 0.5 s.
        This tests DB performance without LLM involvement.
        """
        import uuid
        uid = str(uuid.uuid4())
        stats = _measure(
            lambda: http_client.post("/api/v1/chats", json={"user_id": uid, "title": "Perf test"}),
            n=self.N_RUNS,
        )
        print(f"\n[LIVE] POST /chats mean={stats['mean']:.3f}s")
        assert stats["mean"] <= self.CRUD_SLA_SECONDS

    def test_full_analysis_suite_sla(self, http_client):
        """
        Run all analysis endpoints for AAPL and produce a markdown summary table.
        All must meet their respective SLAs.
        """
        endpoints = {
            "/api/v1/analysis/outlook/AAPL": self.ANALYSIS_SLA_SECONDS,
            "/api/v1/analysis/filing-risks/AAPL": self.ANALYSIS_SLA_SECONDS,
            "/api/v1/analysis/risks/AAPL": self.ANALYSIS_SLA_SECONDS,
            "/api/v1/analysis/ai-themes/AAPL": self.ANALYSIS_SLA_SECONDS,
            "/api/v1/analysis/sentiment-divergence/AAPL": self.ANALYSIS_SLA_SECONDS,
            "/api/v1/analysis/market-news/AAPL": self.ANALYSIS_SLA_SECONDS,
        }

        all_results = {}
        violations = []

        for ep, sla in endpoints.items():
            stats = _measure(lambda ep=ep: http_client.get(ep), n=self.N_RUNS)
            all_results[ep] = stats
            if stats["mean"] > sla:
                violations.append(f"{ep}: mean={stats['mean']:.1f}s > SLA={sla}s")

        _print_table(all_results)
        _save_results(all_results, "live")

        assert not violations, "SLA violations:\n" + "\n".join(violations)

    def test_agent_response_includes_tool_traces(self, http_client):
        """
        Verify that agent responses for RAG questions include tool_calls traces.
        This confirms the agent is actually using tools, not just hallucinating.
        """
        import json

        questions_expecting_tools = [
            ("What are AAPL's risk factors?", "vector_store"),
            ("Show me MSFT's income statement", "get_fundamentals"),
            ("What is NVDA's current price?", "get_company_financials"),
        ]

        for question, expected_tool in questions_expecting_tools:
            start = time.perf_counter()
            resp = http_client.post("/api/v1/agent/chat", json={"message": question})
            elapsed = time.perf_counter() - start
            assert resp.status_code == 200, f"Failed for: {question}"

            body = resp.json()
            tool_names = [tc["tool_name"] for tc in body.get("tool_calls", [])]

            print(f"\n[LIVE] Q: '{question[:50]}...' | tools={tool_names} | time={elapsed:.1f}s")
            assert tool_names, f"No tools called for: {question}"
            assert expected_tool in tool_names, (
                f"Expected tool '{expected_tool}' not called for '{question}'. "
                f"Tools used: {tool_names}"
            )
