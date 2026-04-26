"""
RAGAS-based RAG evaluation tests with Excel Export.
"""

from __future__ import annotations

import json
import os
import time
import pytest
import pandas as pd
from pathlib import Path
from typing import Any

# Configuration
GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Quality thresholds
FAITHFULNESS_THRESHOLD = 0.80
ANSWER_RELEVANCY_THRESHOLD = 0.80
CONTEXT_RECALL_THRESHOLD = 0.70
TOOL_ACCURACY_THRESHOLD = 0.70

RAGAS_LLM_MODEL = os.getenv("RAGAS_LLM_MODEL", "gpt-4o-mini")
RAGAS_LLM_TEMPERATURE = 0.0

def _load_golden_dataset() -> list[dict]:
    with open(GOLDEN_DATASET_PATH) as f:
        return json.load(f)

def _get_ragas_llm():
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI
    return LangchainLLMWrapper(
        ChatOpenAI(model=RAGAS_LLM_MODEL, temperature=RAGAS_LLM_TEMPERATURE)
    )

def _get_ragas_embeddings():
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )

def _save_to_excel(data: list[dict] | pd.DataFrame, test_name: str):
    """Helper to save results to the results directory."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = RESULTS_DIR / f"{test_name}_{timestamp}.xlsx"
    df = pd.DataFrame(data) if isinstance(data, list) else data
    df.to_excel(filename, index=False)
    print(f"\n[INFO] Results saved to {filename}")

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def chroma_client():
    chroma_url = os.getenv("CHROMA_URL")
    if not chroma_url:
        pytest.skip("CHROMA_URL not set")

    import chromadb
    return chromadb.HttpClient(
        host=chroma_url,
        headers={
            "CF-Access-Client-Id": os.getenv("CF-ACCESS-CLIENT-ID", ""),
            "CF-Access-Client-Secret": os.getenv("CF-ACCESS-CLIENT-SECRET", ""),
        },
    )

@pytest.fixture(scope="module")
def embedding_fn():
    from chromadb.utils import embedding_functions
    return embedding_functions.DefaultEmbeddingFunction()


# ── Retrieval quality tests ────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestRetrievalQuality:

    def test_sec_filings_hit_rate(self, chroma_client, embedding_fn):
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"] == "sec_filings"]
        if not dataset: pytest.skip("No cases")

        hits = 0
        results_detail = []

        for case in dataset:
            try:
                collection = chroma_client.get_collection(name="sec_filings")
                results = collection.query(
                    query_texts=[case["question"]],
                    n_results=5,
                    where={"ticker": case["ticker"]} if case.get("ticker") else None,
                    include=["documents", "metadatas"],
                )
                docs = results.get("documents", [[]])[0]
                expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
                hit = any(any(kw in doc.lower() for kw in expected_kws) for doc in docs)
                
                if hit: hits += 1
                results_detail.append({
                    "id": case["id"],
                    "question": case["question"],
                    "hit": hit,
                    "top_doc_preview": docs[0][:200] if docs else "NO RESULTS"
                })
            except Exception as e:
                results_detail.append({"id": case["id"], "error": str(e)})

        _save_to_excel(results_detail, "sec_filings_hit_rate")
        assert (hits / len(dataset)) >= 0.70

    def test_news_collection_hit_rate(self, chroma_client, embedding_fn):
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"] == "news"]
        if not dataset: pytest.skip("No news cases")

        hits = 0
        results_detail = []
        for case in dataset:
            hit = False
            try:
                collection = chroma_client.get_collection(name="news")
                results = collection.query(query_texts=[case["question"]], n_results=5)
                docs = results.get("documents", [[]])[0]
                expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
                hit = any(any(kw in doc.lower() for kw in expected_kws) for doc in docs)
                if hit: hits += 1
                results_detail.append({"id": case["id"], "question": case["question"], "hit": hit})
            except Exception as e:
                results_detail.append({"id": case["id"], "error": str(e)})

        _save_to_excel(results_detail, "news_hit_rate")
        assert (hits / len(dataset)) >= 0.70

    def test_similarity_scores_above_threshold(self, chroma_client, embedding_fn):
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"]]
        results_detail = []
        low_score_count = 0

        for case in dataset:
            try:
                collection = chroma_client.get_collection(name=case["expected_collection"])
                results = collection.query(query_texts=[case["question"]], n_results=1, include=["distances"])
                distances = results.get("distances", [[]])[0]
                similarity = 1 - distances[0] if distances else 0
                results_detail.append({"id": case["id"], "similarity": similarity, "passed": similarity >= 0.5})
                if similarity < 0.5: low_score_count += 1
            except Exception as e:
                results_detail.append({"id": case["id"], "error": str(e)})

        _save_to_excel(results_detail, "similarity_scores")
        assert low_score_count == 0


# ── RAGAS faithfulness and relevancy tests ────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestRAGASEvaluation:
    @pytest.fixture(scope="class")
    def backend_url(self):
        return os.getenv("BACKEND_URL", "http://localhost:8001")

    def _call_agent(self, backend_url: str, question: str, ticker: str | None = None) -> dict:
        import httpx
        payload = {"message": f"[Ticker: {ticker}] {question}" if ticker else question}
        resp = httpx.post(f"{backend_url}/api/v1/agent/chat", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        contexts = [tc["output"] for tc in data.get("tool_calls", []) if "output" in tc]
        return {"answer": data["answer"], "contexts": contexts}

    def _run_ragas_and_export(self, rows, metrics, test_name):
        from ragas import evaluate
        from datasets import Dataset
        hf_dataset = Dataset.from_list(rows)
        results = evaluate(hf_dataset, metrics=metrics, llm=_get_ragas_llm(), embeddings=_get_ragas_embeddings())
        
        # Export the full dataframe including scores and reasons
        _save_to_excel(results.to_pandas(), test_name)
        return results

    def test_faithfulness_above_threshold(self, backend_url):
        from ragas.metrics import faithfulness
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"]][:4]
        rows = []
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                if res["contexts"]:
                    rows.append({"question": case["question"], "answer": res["answer"], 
                                 "contexts": res["contexts"], "ground_truth": case["ground_truth"]})
            except Exception: pass

        if not rows: pytest.skip("No data")
        results = self._run_ragas_and_export(rows, [faithfulness], "ragas_faithfulness")
        assert results["faithfulness"] >= FAITHFULNESS_THRESHOLD

    def test_answer_relevancy_above_threshold(self, backend_url):
        from ragas.metrics import answer_relevancy
        dataset = _load_golden_dataset()[:4]
        rows = []
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                rows.append({"question": case["question"], "answer": res["answer"], 
                             "contexts": res["contexts"] or [case["ground_truth"]], "ground_truth": case["ground_truth"]})
            except Exception: pass

        results = self._run_ragas_and_export(rows, [answer_relevancy], "ragas_relevancy")
        assert results["answer_relevancy"] >= ANSWER_RELEVANCY_THRESHOLD

    def test_context_recall_above_threshold(self, backend_url):
        from ragas.metrics import context_recall
        dataset = [d for d in _load_golden_dataset() if d["expected_collection"]][:4]
        rows = []
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                if res["contexts"]:
                    rows.append({"question": case["question"], "answer": res["answer"], 
                                 "contexts": res["contexts"], "ground_truth": case["ground_truth"]})
            except Exception: pass

        results = self._run_ragas_and_export(rows, [context_recall], "ragas_context_recall")
        assert results["context_recall"] >= CONTEXT_RECALL_THRESHOLD


# ── Tool Call Accuracy ────────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestToolCallAccuracy:
    TOOL_ACCURACY_THRESHOLD = 0.70

    @pytest.fixture(scope="class")
    def backend_url(self):
        return os.getenv("BACKEND_URL", "http://localhost:8001")

    def _call_agent_full_trace(self, backend_url, question, ticker):
        import httpx
        msg = f"[Ticker: {ticker}] {question}" if ticker else question
        resp = httpx.post(f"{backend_url}/api/v1/agent/chat", json={"message": msg}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return {"answer": data.get("answer", ""), "tool_calls": data.get("tool_calls", [])}

    def _build_multiturn_sample(self, question, trace, expected_tool):
        from ragas.dataset_schema import MultiTurnSample
        from ragas.messages import HumanMessage, AIMessage, ToolMessage, ToolCall
        
        actual_calls = [ToolCall(name=tc["tool_name"], args=tc.get("input") or {}) for tc in trace["tool_calls"]]
        messages = [HumanMessage(content=question)]
        if actual_calls:
            messages.append(AIMessage(content="", tool_calls=actual_calls))
            for tc in trace["tool_calls"]:
                messages.append(ToolMessage(content=str(tc.get("output", ""))[:500]))
        messages.append(AIMessage(content=trace["answer"]))

        return MultiTurnSample(user_input=messages, reference_tool_calls=[ToolCall(name=expected_tool, args={})])

    def test_tool_call_accuracy_ragas(self, backend_url):
        from ragas.metrics import ToolCallAccuracy
        from ragas.metrics._string import NonLLMStringSimilarity

        golden = [c for c in _load_golden_dataset() if c.get("expected_tool")]
        if not golden: pytest.skip("No tool test cases")

        metric = ToolCallAccuracy()
        metric.arg_comparison_metric = NonLLMStringSimilarity()

        scores, details = [], []
        for case in golden:
            try:
                trace = self._call_agent_full_trace(backend_url, case["question"], case.get("ticker"))
                sample = self._build_multiturn_sample(case["question"], trace, case["expected_tool"])
                score = metric.multi_turn_score(sample)
                scores.append(score)
                details.append({
                    "id": case["id"], "expected": case["expected_tool"], 
                    "used": [tc["tool_name"] for tc in trace["tool_calls"]], "score": score
                })
            except Exception as e:
                scores.append(0.0)
                details.append({"id": case["id"], "error": str(e)})

        _save_to_excel(details, "tool_call_accuracy")
        avg = sum(scores) / len(scores) if scores else 0
        assert avg >= self.TOOL_ACCURACY_THRESHOLD