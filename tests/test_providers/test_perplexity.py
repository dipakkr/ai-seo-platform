"""Tests for the Perplexity provider."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiseo.providers.perplexity import PerplexityProvider


@pytest.fixture
def provider():
    """Create a PerplexityProvider with a fake API key."""
    with patch("aiseo.providers.perplexity.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(perplexity_api_key="test-key")
        yield PerplexityProvider()


def _make_response(text: str, citations: list[str] | None = None, total_tokens: int = 50):
    """Build a mock Perplexity chat completion response."""
    message = SimpleNamespace(content=text)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(total_tokens=total_tokens)
    resp = SimpleNamespace(choices=[choice], usage=usage)
    if citations is not None:
        resp.citations = citations
    return resp


class TestIsConfigured:
    def test_configured_with_key(self, provider):
        assert provider.is_configured() is True

    def test_not_configured_without_key(self):
        with patch("aiseo.providers.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(perplexity_api_key=None)
            p = PerplexityProvider()
            assert p.is_configured() is False

    def test_not_configured_with_empty_key(self):
        with patch("aiseo.providers.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(perplexity_api_key="")
            p = PerplexityProvider()
            assert p.is_configured() is False


class TestQuery:
    @pytest.mark.asyncio
    async def test_basic_query(self, provider):
        mock_resp = _make_response(
            "Try Notion or Trello for project management.",
            citations=["https://notion.so", "https://trello.com"],
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        provider._get_client = MagicMock(return_value=mock_client)

        result = await provider.query("best project management tools")

        assert result.text == "Try Notion or Trello for project management."
        assert result.citations == ["https://notion.so", "https://trello.com"]
        assert result.model == "sonar"
        assert result.tokens_used == 50
        assert result.latency_ms >= 0

        mock_client.chat.completions.create.assert_awaited_once_with(
            model="sonar",
            messages=[{"role": "user", "content": "best project management tools"}],
        )

    @pytest.mark.asyncio
    async def test_query_without_citations_field(self, provider):
        mock_resp = _make_response(
            "Check out https://example.com and https://other.com for details.",
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        provider._get_client = MagicMock(return_value=mock_client)

        result = await provider.query("test query")

        assert "https://example.com" in result.citations
        assert "https://other.com" in result.citations

    @pytest.mark.asyncio
    async def test_query_empty_response(self, provider):
        mock_resp = SimpleNamespace(choices=[], usage=None)
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        provider._get_client = MagicMock(return_value=mock_client)

        result = await provider.query("test query")

        assert result.text == ""
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_query_not_configured(self):
        with patch("aiseo.providers.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(perplexity_api_key=None)
            p = PerplexityProvider()

            with pytest.raises(RuntimeError, match="not configured"):
                await p.query("test")

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_empty(self, provider):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=ValueError("boom"))
        provider._get_client = MagicMock(return_value=mock_client)

        result = await provider.query("test query")

        assert result.text == ""
        assert result.citations == []


class TestExtractCitations:
    def test_from_citations_field(self):
        resp = SimpleNamespace(citations=["https://a.com", "https://b.com"])
        urls = PerplexityProvider._extract_citations(resp, "some text")
        assert urls == ["https://a.com", "https://b.com"]

    def test_from_text_fallback(self):
        resp = SimpleNamespace()
        text = "See https://example.com and https://other.org for more."
        urls = PerplexityProvider._extract_citations(resp, text)
        assert "https://example.com" in urls
        assert "https://other.org" in urls

    def test_deduplication(self):
        resp = SimpleNamespace(citations=["https://a.com", "https://a.com"])
        urls = PerplexityProvider._extract_citations(resp, "")
        assert urls == ["https://a.com"]

    def test_empty(self):
        resp = SimpleNamespace()
        urls = PerplexityProvider._extract_citations(resp, "no urls here")
        assert urls == []
