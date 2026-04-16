"""
FinancialAgent – LangChain agent wired to MCP tools.

Pattern: Factory Method
  `FinancialAgentFactory.create()` is the single entry point for producing
  a runnable LangChain agent.  Callers never instantiate the agent directly,
  which keeps construction details hidden and makes swapping the underlying
  LLM trivial.

How it works:
  1. A chat model is initialised via `init_chat_model` with the configured
     provider/model string (e.g. "openai:gpt-4.1", "anthropic:claude-opus-4-5").
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

You have access to two powerful tools:

1. **get_company_financials** – Retrieve live market data for any US-listed company
   (market cap, P/E ratio, revenue, EBITDA, free cash flow, analyst ratings, and more).

2. **vector_store** – Store and semantically search financial documents in a
   ChromaDB vector database.
   - Use operation="add" to persist notes, summaries, or earnings data.
   - Use operation="query" to retrieve relevant context before answering.

Guidelines:
- Always fetch fresh data before making claims about a specific company.
- Query the vector store for relevant context before answering research questions.
- Cite figures precisely (include currency and time period when known).
- If data is unavailable or a ticker is invalid, say so clearly.
- Never fabricate financial data.
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
