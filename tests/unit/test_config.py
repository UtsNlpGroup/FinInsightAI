"""
Unit tests for backend/app/core/config.py – Settings.

Tests that environment variable parsing, defaults, and validators work correctly.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSettingsDefaults:
    """Verify default values when no env vars are set."""

    def test_default_app_name(self):
        s = Settings()
        assert s.app_name == "FinsightAI Backend"

    def test_default_environment_is_development(self):
        s = Settings()
        assert s.environment == "development"

    def test_default_debug_is_false(self):
        s = Settings()
        assert s.debug is False

    def test_default_llm_temperature_is_zero(self):
        s = Settings()
        assert s.llm_temperature == 0.0

    def test_default_llm_max_tokens(self):
        s = Settings()
        assert s.llm_max_tokens == 4096

    def test_default_agent_recursion_limit(self):
        s = Settings()
        assert s.agent_recursion_limit == 25

    def test_default_allowed_origins_includes_vite_port(self):
        s = Settings()
        assert "http://localhost:5173" in s.allowed_origins

    def test_default_mcp_server_url(self):
        s = Settings()
        assert "8080" in s.mcp_server_url


class TestSettingsValidation:
    """Verify Pydantic validation rejects invalid values."""

    def test_environment_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            Settings(environment="prod")  # must be "production"

    def test_llm_temperature_rejects_negative(self):
        with pytest.raises(ValidationError):
            Settings(llm_temperature=-0.1)

    def test_llm_temperature_rejects_above_two(self):
        with pytest.raises(ValidationError):
            Settings(llm_temperature=2.1)

    def test_llm_max_tokens_rejects_zero(self):
        with pytest.raises(ValidationError):
            Settings(llm_max_tokens=0)

    def test_agent_max_iterations_rejects_zero(self):
        with pytest.raises(ValidationError):
            Settings(agent_max_iterations=0)


class TestSettingsOriginsParser:
    """Verify comma-separated ALLOWED_ORIGINS string is split into a list."""

    def test_comma_separated_string_is_parsed(self):
        s = Settings(allowed_origins="http://localhost:3000,http://localhost:5173,https://app.example.com")
        assert len(s.allowed_origins) == 3
        assert "http://localhost:3000" in s.allowed_origins
        assert "https://app.example.com" in s.allowed_origins

    def test_list_input_is_preserved(self):
        origins = ["http://a.com", "http://b.com"]
        s = Settings(allowed_origins=origins)
        assert s.allowed_origins == origins

    def test_origins_are_stripped_of_whitespace(self):
        s = Settings(allowed_origins="http://a.com , http://b.com")
        for origin in s.allowed_origins:
            assert origin == origin.strip()


class TestSettingsOverride:
    """Settings can be overridden via constructor arguments (useful in tests)."""

    def test_override_llm_model(self):
        s = Settings(llm_model="openai:gpt-5.4-mini")
        assert s.llm_model == "openai:gpt-5.4-mini"

    def test_override_environment(self):
        s = Settings(environment="production")
        assert s.environment == "production"

    def test_override_temperature(self):
        s = Settings(llm_temperature=0.7)
        assert s.llm_temperature == pytest.approx(0.7)
