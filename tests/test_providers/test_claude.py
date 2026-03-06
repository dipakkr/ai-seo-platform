"""Tests for Claude provider with mocked Anthropic API calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from aiseo.providers.claude import ClaudeProvider


# --- Helpers ---


def _make_response(
    text: str = "mock response",
    input_tokens: int = 50,
    output_tokens: int = 50,
):
    """Build a mock Anthropic Messages API response."""
    content_block = SimpleNamespace(text=text, type="text")
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[content_block], usage=usage)


# --- Tests ---


@pytest.fixture
def provider():
    with patch("aiseo.providers.claude.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(anthropic_api_key="sk-ant-test-key")
        return ClaudeProvider()


class TestIsConfigured:
    def test_configured_with_key(self, provider):
        assert provider.is_configured() is True

    def test_not_configured_without_key(self):
        with patch("aiseo.providers.claude.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(anthropic_api_key=None)
            p = ClaudeProvider()
            assert p.is_configured() is False

    def test_not_configured_with_empty_key(self):
        with patch("aiseo.providers.claude.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(anthropic_api_key="")
            p = ClaudeProvider()
            assert p.is_configured() is False


class TestQuery:
    @pytest.mark.asyncio
    async def test_basic_query(self, provider):
        mock_response = _make_response(text="Claude says hello")

        with patch("aiseo.providers.claude.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages = AsyncMock()
            instance.messages.create = AsyncMock(return_value=mock_response)

            result = await provider.query("best project management tools")

        assert result.text == "Claude says hello"
        assert result.model == "claude-sonnet-4-20250514"
        assert result.tokens_used == 100
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_citations_always_empty(self, provider):
        mock_response = _make_response(text="No web search available")

        with patch("aiseo.providers.claude.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages = AsyncMock()
            instance.messages.create = AsyncMock(return_value=mock_response)

            result = await provider.query("best tools")

        assert result.citations == []

    @pytest.mark.asyncio
    async def test_query_handles_api_error(self, provider):
        from anthropic import APIError

        with patch("aiseo.providers.claude.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages = AsyncMock()
            instance.messages.create = AsyncMock(
                side_effect=APIError(
                    message="server error",
                    request=MagicMock(),
                    body=None,
                )
            )

            result = await provider.query("test query")

        assert result.text == ""
        assert result.citations == []
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_query_raises_when_not_configured(self):
        with patch("aiseo.providers.claude.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(anthropic_api_key=None)
            p = ClaudeProvider()

            with pytest.raises(RuntimeError, match="not configured"):
                await p.query("test")

    @pytest.mark.asyncio
    async def test_query_handles_none_usage(self, provider):
        mock_response = _make_response()
        mock_response.usage = None

        with patch("aiseo.providers.claude.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages = AsyncMock()
            instance.messages.create = AsyncMock(return_value=mock_response)

            result = await provider.query("test")

        assert result.tokens_used is None

    @pytest.mark.asyncio
    async def test_query_handles_empty_content(self, provider):
        mock_response = _make_response()
        mock_response.content = []

        with patch("aiseo.providers.claude.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages = AsyncMock()
            instance.messages.create = AsyncMock(return_value=mock_response)

            result = await provider.query("test")

        assert result.text == ""
