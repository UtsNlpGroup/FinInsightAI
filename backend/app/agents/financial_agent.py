"""
FinancialAgent – LangChain agent wired to MCP tools.

Pattern: Factory Method
  `FinancialAgentFactory.create()` is the single entry point for producing
  a runnable LangChain agent.  Callers never instantiate the agent directly,
  which keeps construction details hidden and makes swapping the underlying
  LLM trivial.

How it works:
  1. A chat model is initialised via `init_chat_model` with the configured
     provider/model string (e.g. "openai:gpt-4.1", "openai:gpt-4o").
  2. `langchain.agents.create_agent` wraps the model and the MCP tools into a
     ready-to-invoke ReAct agent.  The agent handles the tool-call loop
     internally – no manual graph wiring required.

Communication with the MCP server:
  Tools passed to `create_agent` are LangChain `BaseTool` objects loaded from
  the FastMCP HTTP server via `langchain-mcp-adapters`.  Every tool call the
  agent makes is transparently forwarded to the MCP server over HTTP.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool

from app.core.config import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are FinsightAI, an expert financial analyst assistant.

You have access to three powerful tools:

1. **get_company_financials** – Retrieve live market data for any US-listed company
   (market cap, P/E ratio, revenue, EBITDA, free cash flow, analyst ratings, and more).

2. **get_price_history** – Fetch historical OHLCV price data for charting
   (periods: "1mo", "3mo", "6mo", "1y", "2y", "5y").

3. **vector_store** – Store and semantically search financial documents in a
   ChromaDB vector database.
   - Use operation="add" to persist notes, summaries, or earnings data.
   - Use operation="query" to retrieve relevant context before answering.

## Guidelines
- Always fetch fresh data before making claims about a specific company.
- Query the vector store for relevant context before answering research questions.
- Cite figures precisely (include currency and time period when known).
- If data is unavailable or a ticker is invalid, say so clearly.
- Never fabricate financial data.

## Chart Blocks
When you have numeric data worth visualising, embed a chart specification
immediately after the relevant sentence using this **exact** fenced format:

```chart
{"type":"<bar|line|area>","title":"<title>","subtitle":"<optional subtitle>","unit":"<optional unit, e.g. $ or %>","xKey":"<field>","yKeys":[{"key":"<field>","label":"<label>","color":"<optional hex>"}],"data":[...]}
```

Rules for chart blocks:
- **line / area**: use for time-series data (price history). xKey should be "date".
  Include only "close" (and optionally "high"/"low") in yKeys. Max 60 data points.
- **bar**: use for categorical comparisons (e.g. revenue vs EBITDA vs free cash flow).
  Each data row is {name:"Metric", value:number}.
  xKey = "name", yKeys = [{"key":"value","label":"Value","color":"#7C3AED"}].
- Always include a human-readable "title" and optionally "subtitle".
- Use "unit":"$B" for billions, "$M" for millions, "$" for raw dollar amounts, "%" for percentages.
- Do not wrap the JSON in extra quotes or escape characters—emit raw JSON on one line.
- You may include multiple chart blocks in a single response (one per concept).

Example bar chart for financial metrics:
```chart
{"type":"bar","title":"Apple Key Financials (TTM)","subtitle":"USD Billions","unit":"$B","xKey":"name","yKeys":[{"key":"value","label":"USD Billions","color":"#7C3AED"}],"data":[{"name":"Revenue","value":383.3},{"name":"Gross Profit","value":169.1},{"name":"EBITDA","value":125.8},{"name":"Free Cash Flow","value":99.6}]}
```
"""


class FinancialAgentFactory:
    """
    Factory responsible for creating a LangChain financial agent.

    Using the Factory Method pattern means AgentService stays decoupled
    from construction details.  To swap the model provider or change
    agent behaviour, only this class needs to change.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, tools: list[BaseTool]) -> Any:
        """
        Instantiate and return a LangChain agent backed by MCP tools.

        The agent is created with `langchain.agents.create_agent`, which
        accepts either a model-ID string or a pre-configured `BaseChatModel`
        instance.  We pass a pre-configured model so that temperature and
        max_tokens are respected.

        Args:
            tools: LangChain tools loaded from the FastMCP HTTP server via
                   `langchain-mcp-adapters`.  Each tool transparently
                   delegates its execution to the MCP server over HTTP.

        Returns:
            A runnable LangChain agent that supports `.ainvoke()` and
            `.astream_events()`.
        """
        llm = init_chat_model(
            self._settings.llm_model,
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_tokens,
        )

        agent = create_agent(llm, tools)

        logger.info(
            "FinancialAgent created | model=%s | tools=%s",
            self._settings.llm_model,
            [t.name for t in tools],
        )
        return agent

    @property
    def system_prompt(self) -> str:
        """Expose the system prompt so the service layer can inject it."""
        return _SYSTEM_PROMPT
