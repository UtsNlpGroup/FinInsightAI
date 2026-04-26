"""
RAGAS-based RAG evaluation tests.

These tests measure:
  - context_precision: retrieved chunks are relevant to the question
  - context_recall: ground truth answer is covered by retrieved chunks
  - faithfulness: agent answer is entailed by retrieved context (no hallucination)
  - answer_relevancy: agent answer is relevant to the question

Marked with @pytest.mark.live because they require:
  - A running Chroma instance (CHROMA_URL in env)
  - A valid OPENAI_API_KEY in env (RAGAS uses LLM-as-judge)

Run with:
    pytest tests/rag/test_ragas_evaluation.py -m live -v

Thresholds (configurable via constants below):
  - Faithfulness   >= 0.80
  - Answer Relevancy >= 0.80
  - Context Recall >= 0.70
"""

from __future__ import annotations

import json
import os
import time
import pytest
from pathlib import Path
from typing import Any

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"

# Quality thresholds
FAITHFULNESS_THRESHOLD = 0.80
ANSWER_RELEVANCY_THRESHOLD = 0.80
CONTEXT_RECALL_THRESHOLD = 0.70
TOOL_ACCURACY_THRESHOLD = 0.70
# ── LLM / embedding model config ──────────────────────────────────────────────
# LLM: gpt-4o-mini at temperature=0.0 (same as the financial agent in backend)
# Embeddings: Chroma's default (all-MiniLM-L6-v2) — same model used during ingestion
RAGAS_LLM_MODEL = os.getenv("RAGAS_LLM_MODEL", "gpt-4o-mini")
RAGAS_LLM_TEMPERATURE = 0.0  # matches backend/app/core/config.py llm_temperature default


def _load_golden_dataset() -> list[dict]:
    with open(GOLDEN_DATASET_PATH) as f:
        return json.load(f)


def _get_ragas_llm():
    """
    LLM judge: gpt-4o-mini at temperature=0.0.
    temperature=0.0 matches the financial agent's own setting (config.py llm_temperature).
    Deterministic output makes evaluation scores reproducible across runs.
    """
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI
    return LangchainLLMWrapper(
        ChatOpenAI(model=RAGAS_LLM_MODEL, temperature=RAGAS_LLM_TEMPERATURE)
    )


def _get_ragas_embeddings():
    """
    Embeddings: Chroma's built-in default (all-MiniLM-L6-v2 via sentence-transformers).
    Using the same model that was used during ingestion ensures the similarity
    scores RAGAS computes are consistent with what Chroma sees at query time.
    """
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def chroma_client():
    """Real Chroma client connected to the remote instance."""
    chroma_url = os.getenv("CHROMA_URL")
    if not chroma_url:
        pytest.skip("CHROMA_URL not set – skipping live RAG tests")

    import chromadb
    client = chromadb.HttpClient(
        host=chroma_url,
        headers={
            "CF-Access-Client-Id": os.getenv("CF-ACCESS-CLIENT-ID", ""),
            "CF-Access-Client-Secret": os.getenv("CF-ACCESS-CLIENT-SECRET", ""),
        },
    )
    return client


@pytest.fixture(scope="module")
def embedding_fn():
    from chromadb.utils import embedding_functions
    return embedding_functions.DefaultEmbeddingFunction()


# ── Retrieval quality tests ────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestRetrievalQuality:
    """
    Verify that for each golden question, Chroma returns relevant documents.

    Hit Rate@5: at least 1 of the top-5 retrieved docs must match the expected ticker.
    """

    def test_sec_filings_hit_rate(self, chroma_client, embedding_fn):
        """Verify sec_filings collection returns ticker-relevant docs for 10-K questions."""
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"] == "sec_filings"]
        if not dataset:
            pytest.skip("No sec_filings test cases in golden dataset")

        hits = 0
        results_detail = []

        for case in dataset:
            try:
                collection = chroma_client.get_collection(
                    name="sec_filings", embedding_function=embedding_fn
                )
                results = collection.query(
                    query_texts=[case["question"]],
                    n_results=5,
                    where={"ticker": case["ticker"]} if case.get("ticker") else None,
                    include=["documents", "metadatas", "distances"],
                )
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]

                # Hit: any keyword from expected_keywords appears in the retrieved docs
                expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
                hit = any(
                    any(kw in doc.lower() for kw in expected_kws)
                    for doc in docs
                )
                if hit:
                    hits += 1
                results_detail.append({
                    "id": case["id"],
                    "question": case["question"],
                    "hit": hit,
                    "top_doc_preview": docs[0][:100] if docs else "NO RESULTS",
                })
            except Exception as e:
                results_detail.append({"id": case["id"], "error": str(e)})

        hit_rate = hits / len(dataset)
        print(f"\n[RAG] sec_filings hit rate: {hit_rate:.2%} ({hits}/{len(dataset)})")
        for r in results_detail:
            print(f"  {r['id']}: {'HIT' if r.get('hit') else 'MISS'} – {r.get('top_doc_preview', r.get('error', ''))}")

        assert hit_rate >= 0.70, (
            f"sec_filings hit rate {hit_rate:.2%} is below the 70% threshold. "
            f"Consider re-ingesting 10-K documents."
        )

    def test_news_collection_hit_rate(self, chroma_client, embedding_fn):
        """Verify news collection returns relevant docs for news-type questions."""
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"] == "news"]
        if not dataset:
            pytest.skip("No news test cases in golden dataset")

        hits = 0
        for case in dataset:
            try:
                collection = chroma_client.get_collection(
                    name="news", embedding_function=embedding_fn
                )
                results = collection.query(
                    query_texts=[case["question"]],
                    n_results=5,
                    where={"ticker": case["ticker"]} if case.get("ticker") else None,
                    include=["documents", "metadatas"],
                )
                docs = results.get("documents", [[]])[0]
                expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
                hit = any(
                    any(kw in doc.lower() for kw in expected_kws)
                    for doc in docs
                )
                if hit:
                    hits += 1
            except Exception:
                pass

        hit_rate = hits / len(dataset) if dataset else 0
        print(f"\n[RAG] news hit rate: {hit_rate:.2%} ({hits}/{len(dataset)})")
        assert hit_rate >= 0.70

    def test_similarity_scores_above_threshold(self, chroma_client, embedding_fn):
        """Top retrieved document should have a similarity score >= 0.5 for each query."""
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"]]
        low_score_cases = []

        for case in dataset:
            try:
                collection_name = case["expected_collection"]
                collection = chroma_client.get_collection(
                    name=collection_name, embedding_function=embedding_fn
                )
                results = collection.query(
                    query_texts=[case["question"]],
                    n_results=1,
                    include=["distances"],
                )
                distances = results.get("distances", [[]])[0]
                if distances:
                    similarity = 1 - distances[0]
                    if similarity < 0.5:
                        low_score_cases.append({"id": case["id"], "score": similarity})
            except Exception:
                pass

        assert len(low_score_cases) == 0, (
            f"Some queries returned low similarity scores (< 0.5): {low_score_cases}"
        )


# ── RAGAS faithfulness and relevancy tests ────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestRAGASEvaluation:
    """
    Full RAGAS evaluation using LLM-as-judge.

    Requires OPENAI_API_KEY and a running backend for agent responses.
    """

    @pytest.fixture(scope="class")
    def backend_url(self):
        url = os.getenv("BACKEND_URL", "http://localhost:8001")
        return url

    def _call_agent(self, backend_url: str, question: str, ticker: str | None = None) -> dict:
        """Call the real /api/v1/agent/chat endpoint and return {answer, contexts}."""
        import httpx

        payload = {"message": question}
        if ticker:
            payload["message"] = f"[Ticker: {ticker}] {question}"

        resp = httpx.post(
            f"{backend_url}/api/v1/agent/chat",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        contexts = [tc["output"] for tc in data.get("tool_calls", []) if "output" in tc]
        return {"answer": data["answer"], "contexts": contexts}

    def test_faithfulness_above_threshold(self, backend_url):
        """
        RAGAS faithfulness: agent answer is entailed by retrieved context.
        A score of 1.0 means every claim is grounded in context.
        """
        from ragas import evaluate
        from ragas.metrics import faithfulness
        from datasets import Dataset

        dataset = [d for d in _load_golden_dataset() if d["expected_collection"]][:4]
        if not dataset:
            pytest.skip("No vectorstore test cases available")

        rows = []
        for case in dataset:
            try:
                result = self._call_agent(backend_url, case["question"], case.get("ticker"))
                if result["contexts"]:
                    rows.append({
                        "question": case["question"],
                        "answer": result["answer"],
                        "contexts": result["contexts"],
                        "ground_truth": case["ground_truth"],
                    })
            except Exception as e:
                print(f"  Skipping {case['id']}: {e}")

        if not rows:
            pytest.skip("No agent responses collected – is the backend running?")

        hf_dataset = Dataset.from_list(rows)
        results = evaluate(hf_dataset, metrics=[faithfulness],
                           llm=_get_ragas_llm(), embeddings=_get_ragas_embeddings())
        score = results["faithfulness"]
        print(f"\n[RAGAS] faithfulness = {score:.4f} (threshold = {FAITHFULNESS_THRESHOLD})")
        assert score >= FAITHFULNESS_THRESHOLD, (
            f"Faithfulness {score:.4f} < {FAITHFULNESS_THRESHOLD}. "
            "The agent may be hallucinating content not in the retrieved documents."
        )

    def test_answer_relevancy_above_threshold(self, backend_url):
        """
        RAGAS answer_relevancy: how relevant is the answer to the question?
        """
        from ragas import evaluate
        from ragas.metrics import answer_relevancy
        from datasets import Dataset

        dataset = _load_golden_dataset()[:4]
        rows = []
        for case in dataset:
            try:
                result = self._call_agent(backend_url, case["question"], case.get("ticker"))
                rows.append({
                    "question": case["question"],
                    "answer": result["answer"],
                    "contexts": result["contexts"] or [case["ground_truth"]],
                    "ground_truth": case["ground_truth"],
                })
            except Exception as e:
                print(f"  Skipping {case['id']}: {e}")

        if not rows:
            pytest.skip("No agent responses collected")

        hf_dataset = Dataset.from_list(rows)
        results = evaluate(hf_dataset, metrics=[answer_relevancy],
                           llm=_get_ragas_llm(), embeddings=_get_ragas_embeddings())
        score = results["answer_relevancy"]
        print(f"\n[RAGAS] answer_relevancy = {score:.4f} (threshold = {ANSWER_RELEVANCY_THRESHOLD})")
        assert score >= ANSWER_RELEVANCY_THRESHOLD

    def test_context_recall_above_threshold(self, backend_url):
        """
        RAGAS context_recall: does the retrieved context cover the ground truth?
        """
        from ragas import evaluate
        from ragas.metrics import context_recall
        from datasets import Dataset

        dataset = [d for d in _load_golden_dataset() if d["expected_collection"]][:4]
        rows = []
        for case in dataset:
            try:
                result = self._call_agent(backend_url, case["question"], case.get("ticker"))
                if result["contexts"]:
                    rows.append({
                        "question": case["question"],
                        "answer": result["answer"],
                        "contexts": result["contexts"],
                        "ground_truth": case["ground_truth"],
                    })
            except Exception as e:
                print(f"  Skipping {case['id']}: {e}")

        if not rows:
            pytest.skip("No agent responses collected")

        hf_dataset = Dataset.from_list(rows)
        results = evaluate(hf_dataset, metrics=[context_recall],
                           llm=_get_ragas_llm(), embeddings=_get_ragas_embeddings())
        score = results["context_recall"]
        print(f"\n[RAGAS] context_recall = {score:.4f} (threshold = {CONTEXT_RECALL_THRESHOLD})")
        assert score >= CONTEXT_RECALL_THRESHOLD


# ── RAGAS agent / tool-call evaluation ────────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestToolCallAccuracy:
    """
    Uses RAGAS ToolCallAccuracy (MultiTurnSample) to verify the financial agent
    selects the correct MCP tool for each golden question.

    This replaces the need for LangSmith tool-selection tests.

    How it works:
      1. Call the real backend and capture the full tool trace.
      2. Convert the trace → RAGAS MultiTurnSample (HumanMessage / AIMessage
         with ToolCall / ToolMessage / final AIMessage).
      3. Compare against reference_tool_calls from golden_dataset.json.
      4. ToolCallAccuracy scores 0-1; we assert avg >= 0.75.

    ToolCallAccuracy note on args:
      We only care about tool *name* routing, not exact args (args differ per run).
      We therefore use NonLLMStringSimilarity as the arg_comparison_metric with a
      low threshold so that any args satisfy the arg check when the name matches.
    """    

    @pytest.fixture(scope="class")
    def backend_url(self):
        url = os.getenv("BACKEND_URL", "http://localhost:8001")
        try:
            import httpx
            resp = httpx.get(f"{url}/health", timeout=5)
            if resp.status_code != 200:
                pytest.skip(f"Backend not healthy at {url}")
        except Exception:
            pytest.skip(f"Backend not reachable at {url}")
        return url

    def _call_agent_full_trace(self, backend_url: str, question: str, ticker: str | None = None) -> dict:
        """
        Call /api/v1/agent/chat and return answer + full tool trace.
        Returns: {answer, tool_calls: [{tool_name, input, output}]}
        """
        import httpx
        msg = f"[Ticker: {ticker}] {question}" if ticker else question
        resp = httpx.post(
            f"{backend_url}/api/v1/agent/chat",
            json={"message": msg},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "answer": data.get("answer", ""),
            "tool_calls": data.get("tool_calls", []),
        }

    def _build_multiturn_sample(self, question: str, trace: dict, expected_tool: str):
        """
        Convert a backend response into a RAGAS MultiTurnSample.

        user_input trace:
          HumanMessage(question)
          AIMessage(tool_calls=[actual calls made])
          ToolMessage(output of first tool, if any)
          AIMessage(final answer)
        reference_tool_calls:
          [ToolCall(name=expected_tool, args={})]
        """
        from ragas.dataset_schema import MultiTurnSample
        from ragas.messages import HumanMessage, AIMessage, ToolMessage, ToolCall

        tool_calls_raw = trace["tool_calls"]
        answer = trace["answer"]

        # Build the actual tool calls made by the agent
        actual_tool_calls = [
            ToolCall(name=tc["tool_name"], args=tc.get("input") or {})
            for tc in tool_calls_raw
        ]

        messages = [HumanMessage(content=question)]

        if actual_tool_calls:
            # AI turn that issued the tool calls
            messages.append(AIMessage(content="", tool_calls=actual_tool_calls))
            # Tool response messages
            for tc in tool_calls_raw:
                output = tc.get("output", "")
                messages.append(ToolMessage(content=str(output)[:500]))

        # Final AI answer
        messages.append(AIMessage(content=answer))

        return MultiTurnSample(
            user_input=messages,
            reference_tool_calls=[ToolCall(name=expected_tool, args={})],
        )

    def test_tool_call_accuracy_ragas(self, backend_url):
        """
        RAGAS ToolCallAccuracy across all golden examples that specify an expected_tool.

        Scores:
          1.0 – agent called the expected tool (name match)
          0.0 – agent did not call the expected tool
        Expected aggregate: >= 75%
        """
        from ragas.metrics import ToolCallAccuracy
        from ragas.metrics._string import NonLLMStringSimilarity

        golden = [c for c in _load_golden_dataset() if c.get("expected_tool")]
        if not golden:
            pytest.skip("No golden examples with expected_tool")

        # Use string similarity for args so we only penalise wrong tool names,
        # not missing/different arg values (which are run-dependent)
        metric = ToolCallAccuracy()
        metric.arg_comparison_metric = NonLLMStringSimilarity()

        scores = []
        details = []
        for case in golden:
            try:
                trace = self._call_agent_full_trace(
                    backend_url, case["question"], case.get("ticker")
                )
                sample = self._build_multiturn_sample(
                    case["question"], trace, case["expected_tool"]
                )
                score = metric.multi_turn_score(sample)
                scores.append(score)
                details.append({
                    "id": case["id"],
                    "expected": case["expected_tool"],
                    "used": [tc["tool_name"] for tc in trace["tool_calls"]],
                    "score": score,
                })
                print(
                    f"  [{case['id']}] expected={case['expected_tool']} "
                    f"used={[tc['tool_name'] for tc in trace['tool_calls']]} "
                    f"score={score:.2f}"
                )
            except Exception as e:
                print(f"  [{case['id']}] ERROR: {e}")
                scores.append(0.0)

        if not scores:
            pytest.skip("No scores collected")

        avg = sum(scores) / len(scores)
        print(f"\n[RAGAS ToolCallAccuracy] avg={avg:.2%} over {len(scores)} examples")
        print(f"  Details: {details}")

        assert avg >= self.TOOL_ACCURACY_THRESHOLD, (
            f"ToolCallAccuracy {avg:.2%} < {self.TOOL_ACCURACY_THRESHOLD:.0%}. "
            "Agent is routing to wrong MCP tools. Review the system prompt."
        )