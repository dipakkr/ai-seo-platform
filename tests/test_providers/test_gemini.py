"""Tests for Gemini provider with mocked API calls."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from aiseo.providers.gemini import GeminiProvider, _extract_citations


@pytest.fixture()
def _configured_key():
    """Patch settings so the provider sees a configured API key."""
    with patch("aiseo.providers.gemini.get_settings") as mock_settings:
        settings = MagicMock()
        settings.google_api_key = "test-key-123"
        mock_settings.return_value = settings
        yield


@pytest.fixture()
def provider(_configured_key):
    return GeminiProvider()


def _make_web_chunk(uri: str):
    web = MagicMock()
    web.uri = uri
    chunk = MagicMock()
    chunk.web = web
    return chunk


def _make_response(text="Some response", chunks=None, total_tokens=42):
    """Build a mock Gemini response."""
    metadata = MagicMock()
    metadata.grounding_chunks = chunks or []

    candidate = MagicMock()
    candidate.grounding_metadata = metadata

    usage = MagicMock()
    usage.total_token_count = total_tokens

    response = MagicMock()
    response.text = text
    response.candidates = [candidate]
    response.usage_metadata = usage
    return response


class TestIsConfigured:
    def test_configured(self, provider):
        assert provider.is_configured() is True

    def test_not_configured_none(self):
        with patch("aiseo.providers.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(google_api_key=None)
            p = GeminiProvider()
            assert p.is_configured() is False

    def test_not_configured_empty(self):
        with patch("aiseo.providers.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(google_api_key="")
            p = GeminiProvider()
            assert p.is_configured() is False


class TestQuery:
    @pytest.mark.asyncio
    async def test_successful_query(self, provider):
        chunks = [
            _make_web_chunk("https://example.com"),
            _make_web_chunk("https://other.com"),
        ]
        mock_response = _make_response(
            text="Gemini says hello", chunks=chunks, total_tokens=100
        )

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("aiseo.providers.gemini.genai.Client", return_value=mock_client):
            result = await provider.query("best project management tools")

        assert result.text == "Gemini says hello"
        assert result.model == "gemini-2.0-flash"
        assert result.tokens_used == 100
        assert result.latency_ms >= 0
        assert "https://example.com" in result.citations
        assert "https://other.com" in result.citations

    @pytest.mark.asyncio
    async def test_not_configured_raises(self):
        with patch("aiseo.providers.gemini.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(google_api_key=None)
            p = GeminiProvider()
            with pytest.raises(RuntimeError, match="not configured"):
                await p.query("test")

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self, provider):
        from google.genai.errors import ClientError

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=ClientError(400, "boom")
        )

        with patch("aiseo.providers.gemini.genai.Client", return_value=mock_client):
            result = await provider.query("test query")

        assert result.text == ""
        assert result.citations == []
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_no_grounding_metadata(self, provider):
        candidate = MagicMock()
        candidate.grounding_metadata = None

        response = MagicMock()
        response.text = "No grounding"
        response.candidates = [candidate]
        response.usage_metadata = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=response)

        with patch("aiseo.providers.gemini.genai.Client", return_value=mock_client):
            result = await provider.query("test")

        assert result.text == "No grounding"
        assert result.citations == []
        assert result.tokens_used is None


class TestExtractCitations:
    def test_extracts_unique_urls(self):
        chunks = [
            _make_web_chunk("https://a.com"),
            _make_web_chunk("https://b.com"),
            _make_web_chunk("https://a.com"),  # duplicate
        ]
        response = _make_response(chunks=chunks)
        urls = _extract_citations(response)
        assert urls == ["https://a.com", "https://b.com"]

    def test_no_candidates(self):
        response = MagicMock()
        response.candidates = []
        assert _extract_citations(response) == []

    def test_no_web_attribute(self):
        chunk = MagicMock()
        chunk.web = None
        response = _make_response(chunks=[chunk])
        assert _extract_citations(response) == []
