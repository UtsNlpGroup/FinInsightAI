"""
RAGAS-based RAG evaluation tests.
Includes: Retrieval Quality (Chroma/OpenAI), Ragas Metrics, and Tool Use Accuracy.
"""

from __future__ import annotations

import json
import os
import time
import pytest
import pandas as pd
from pathlib import Path
from typing import Any

# ChromaDB Imports
import chromadb
from chromadb.utils import embedding_functions

# --- CONFIGURATION ---
GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Quality thresholds
FAITHFULNESS_THRESHOLD = 0.80
ANSWER_RELEVANCY_THRESHOLD = 0.80
CONTEXT_RECALL_THRESHOLD = 0.70
TOOL_ACCURACY_THRESHOLD = 0.70  # Restored

# Environment variables
RAGAS_LLM_MODEL = os.getenv("RAGAS_LLM_MODEL", "gpt-4o-mini")
RAGAS_LLM_TEMPERATURE = 0.0
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define the OpenAI Embedding Function for ChromaDB queries
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)

# --- HELPERS ---

def _load_golden_dataset() -> list[dict]:
    if not GOLDEN_DATASET_PATH.exists():
        pytest.skip(f"Golden dataset not found at {GOLDEN_DATASET_PATH}")
    with open(GOLDEN_DATASET_PATH) as f:
        return json.load(f)

def _get_ragas_llm():
    from openai import OpenAI
    from ragas.llms import llm_factory

    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()
    return llm_factory(
        RAGAS_LLM_MODEL,
        client=client,
        temperature=RAGAS_LLM_TEMPERATURE,
    )


def _get_ragas_embeddings():
    from openai import OpenAI
    from ragas.embeddings import OpenAIEmbeddings

    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()
    return OpenAIEmbeddings(client=client, model="text-embedding-3-small")

def _save_to_excel(data: list[dict] | pd.DataFrame, test_name: str):
    date_str = time.strftime("%Y%m%d")
    filename = RESULTS_DIR / f"{test_name}_{date_str}.xlsx"
    df = pd.DataFrame(data) if isinstance(data, list) else data
    df = df.loc[:, ~df.columns.duplicated()]
    df.to_excel(filename, index=False)
    print(f"\n[INFO] Results saved to {filename}")

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def chroma_client():
    chroma_url = os.getenv("CHROMA_URL")
    if not chroma_url:
        pytest.skip("CHROMA_URL not set")

    return chromadb.HttpClient(
        host=chroma_url,
        headers={
            "CF-Access-Client-Id": os.getenv("CF-ACCESS-CLIENT-ID", ""),
            "CF-Access-Client-Secret": os.getenv("CF-ACCESS-CLIENT-SECRET", ""),
        },
    )

# ── Retrieval Quality Logic ──────────────────────────────────────────────────

_COLLECTION_MAP_CHROMA = {"sec_filings": "sec_filings_chroma", "news": "news_chroma"}
_COLLECTION_MAP_OPENAI = {"sec_filings": "sec_filings_openai", "news": "news_openai"}

def _run_hit_rate_test(chroma_client, target_collection, output_name, ef=None):
    dataset = [d for d in _load_golden_dataset() if d["expected_collection"] == target_collection.split('_')[0]]
    hits, results_detail = 0, []
    
    for case in dataset:
        try:
            collection = chroma_client.get_collection(name=target_collection, embedding_function=ef)
            results = collection.query(
                query_texts=[case["question"]], 
                n_results=5, 
                where={"ticker": case["ticker"]} if case.get("ticker") else None
            )
            docs = results.get("documents", [[]])[0]
            hit = any(any(kw.lower() in doc.lower() for kw in case.get("expected_keywords", [])) for doc in docs)
            if hit: hits += 1
            results_detail.append({"id": case["id"], "question": case["question"], "hit": hit})
        except Exception as e:
            results_detail.append({"id": case["id"], "error": str(e)})
            
    _save_to_excel(results_detail, f"hit_rate_{output_name}")
    assert (hits / len(dataset)) >= 0.70

def _run_similarity_scores(chroma_client, collection_map, output_prefix, ef=None):
    dataset = [d for d in _load_golden_dataset() if d["expected_collection"]]
    results_detail, low_score_count = [], 0
    
    for case in dataset:
        physical_col = collection_map.get(case["expected_collection"], case["expected_collection"])
        try:
            collection = chroma_client.get_collection(name=physical_col, embedding_function=ef)
            results = collection.query(
                query_texts=[case["question"]], 
                n_results=1, 
                where={"ticker": case["ticker"]} if case.get("ticker") else None,
                include=["distances"]
            )
            dist = results.get("distances", [[]])[0][0] if results.get("distances") else 1.0
            similarity = 1 - dist
            results_detail.append({"id": case["id"], "similarity": similarity, "passed": similarity >= 0.5})
            if similarity < 0.5: low_score_count += 1
        except Exception as e:
            results_detail.append({"id": case["id"], "error": str(e)})
            
    _save_to_excel(results_detail, f"similarity_{output_prefix}")
    assert low_score_count == 0

# ── Test Classes ─────────────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.rag
class TestRetrievalQualityChroma:
    def test_sec_filings_hit_rate(self, chroma_client):
        _run_hit_rate_test(chroma_client, "sec_filings_chroma", "sec_chroma")
    def test_news_hit_rate(self, chroma_client):
        _run_hit_rate_test(chroma_client, "news_chroma", "news_chroma")
    def test_similarity_scores(self, chroma_client):
        _run_similarity_scores(chroma_client, _COLLECTION_MAP_CHROMA, "chroma")

@pytest.mark.live
@pytest.mark.rag
class TestRetrievalQualityOpenAI:
    def test_sec_filings_hit_rate(self, chroma_client):
        _run_hit_rate_test(chroma_client, "sec_filings_openai", "sec_openai", ef=openai_ef)
    def test_news_hit_rate(self, chroma_client):
        _run_hit_rate_test(chroma_client, "news_openai", "news_openai", ef=openai_ef)
    def test_similarity_scores(self, chroma_client):
        _run_similarity_scores(chroma_client, _COLLECTION_MAP_OPENAI, "openai", ef=openai_ef)

# ── RAGAS & Tool Evaluation ──────────────────────────────────────────────────

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
        
        # Extract context and tool names
        tool_calls = data.get("tool_calls", [])
        tool_names = [tc.get("name") for tc in tool_calls if "name" in tc]
        raw_outputs = [tc["output"] for tc in tool_calls if "output" in tc]
        
        clean_contexts = []
        for ctx in raw_outputs:
            if isinstance(ctx, str): clean_contexts.append(ctx)
            elif isinstance(ctx, list):
                for item in ctx:
                    if isinstance(item, dict): clean_contexts.append(item.get("text") or str(item))
                    else: clean_contexts.append(str(item))
        
        return {"answer": data["answer"], "contexts": clean_contexts, "tool_names": tool_names}

    def _run_ragas_and_export(self, rows, metrics, test_name):
        if not rows: pytest.fail(f"No valid rows for {test_name}")
        from ragas import evaluate
        from datasets import Dataset
        hf_dataset = Dataset.from_list(rows)
        results = evaluate(hf_dataset, metrics=metrics, llm=_get_ragas_llm(), embeddings=_get_ragas_embeddings())
        _save_to_excel(results.to_pandas(), test_name)
        return results

    def test_faithfulness(self, backend_url):
        from ragas.metrics.collections import faithfulness
        dataset = [d for d in _load_golden_dataset() if d.get("expected_collection")][:4]
        rows = []
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                if res["contexts"]:
                    rows.append({"question": case["question"], "answer": res["answer"], "contexts": res["contexts"], "ground_truth": case["ground_truth"]})
            except Exception: pass
        results = self._run_ragas_and_export(rows, [faithfulness], "ragas_faithfulness")
        faithfulness_score = sum(results["faithfulness"]) / len(results["faithfulness"])
        assert faithfulness_score >= FAITHFULNESS_THRESHOLD

    def test_answer_relevancy(self, backend_url):
        from ragas.metrics.collections import answer_relevancy
        dataset = _load_golden_dataset()[:4]
        rows = []
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                rows.append({"question": case["question"], "answer": res["answer"], "contexts": res["contexts"] or [case["ground_truth"]], "ground_truth": case["ground_truth"]})
            except Exception: pass
        results = self._run_ragas_and_export(rows, [answer_relevancy], "ragas_relevancy")
        assert results["answer_relevancy"] >= ANSWER_RELEVANCY_THRESHOLD

    def test_context_recall(self, backend_url):
        from ragas.metrics.collections import context_recall
        dataset = [d for d in _load_golden_dataset() if d.get("expected_collection")][:4]
        rows = []
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                if res["contexts"]:
                    rows.append({"question": case["question"], "answer": res["answer"], "contexts": res["contexts"], "ground_truth": case["ground_truth"]})
            except Exception: pass
        results = self._run_ragas_and_export(rows, [context_recall], "ragas_context_recall")
        assert results["context_recall"] >= CONTEXT_RECALL_THRESHOLD
         
    def test_tool_use_accuracy(self, backend_url):
        """Restored: Checks if the agent selected the correct tool based on expected_collection."""
        dataset = [d for d in _load_golden_dataset() if "expected_collection" in d]
        hits, results_detail = 0, []
        
        for case in dataset:
            try:
                res = self._call_agent(backend_url, case["question"], case.get("ticker"))
                # Logic: if expected is 'news', check if tool_names contains 'get_news' (adjust names as per your tool names)
                expected_map = {"news": "get_news", "sec_filings": "search_sec_filings"}
                expected_tool = expected_map.get(case["expected_collection"])
                
                hit = expected_tool in res["tool_names"] if expected_tool else True
                if hit: hits += 1
                results_detail.append({
                    "id": case["id"], "question": case["question"], 
                    "expected": expected_tool, "called": res["tool_names"], "hit": hit
                })
            except Exception as e:
                results_detail.append({"id": case["id"], "error": str(e)})

        _save_to_excel(results_detail, "tool_accuracy")
        assert (hits / len(dataset)) >= TOOL_ACCURACY_THRESHOLD