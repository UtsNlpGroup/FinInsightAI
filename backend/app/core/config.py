"""
Application configuration loaded from environment variables.

Uses Pydantic BaseSettings so every field can be overridden via env-vars
or a .env file without touching code.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "FinsightAI Backend"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False)

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )

    # ── MCP Server ────────────────────────────────────────────────────────────
    mcp_server_url: str = Field(
        default="http://localhost:8080/mcp",
        description="Full URL of the FastMCP HTTP server.",
    )

    # ── LLM Provider ─────────────────────────────────────────────────────────
    # Passed to langchain.chat_models.init_chat_model, e.g.:
    #   "openai:gpt-4.1", "anthropic:claude-opus-4-5", "ollama:llama3"
    llm_model: str = Field(default="openai:gpt-4.1")
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4096, gt=0)

    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")

    # ── Agent ─────────────────────────────────────────────────────────────────
    agent_max_iterations: int = Field(default=10, gt=0)
    agent_recursion_limit: int = Field(default=25, gt=0)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
