"""Tests for ChatGPT provider with mocked OpenAI API calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from aiseo.providers.chatgpt import ChatGPTProvider, _extract_citations


# --- Helpers to build mock response objects ---


def _make_annotation(ann_type: str, url: str | None = None):
    return SimpleNamespace(type=ann_type, url=url)


def _make_block(annotations=None):
    return SimpleNamespace(annotations=annotations or [])


def _make_output_item(content=None):
    return SimpleNamespace(content=content)


def _make_response(
    output_text: str = "mock response",
    output_items=None,
    total_tokens: int = 100,
):
    """Build a mock Responses API response."""
    if output_items is None:
        output_items = [_make_output_item(content=[_make_block()])]
    usage = SimpleNamespace(total_tokens=total_tokens)
    return SimpleNamespace(
        output_text=output_text,
        output=output_items,
        usage=usage,
    )


# --- Tests ---


@pytest.fixture
def provider():
    with patch("aiseo.providers.chatgpt.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(openai_api_key="sk-test-key")
        return ChatGPTProvider()


class TestIsConfigured:
    def test_configured_with_key(self, provider):
        assert provider.is_configured() is True

    def test_not_configured_without_key(self):
        with patch("aiseo.providers.chatgpt.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key=None)
            p = ChatGPTProvider()
            assert p.is_configured() is False

    def test_not_configured_with_empty_key(self):
        with patch("aiseo.providers.chatgpt.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="")
            p = ChatGPTProvider()
            assert p.is_configured() is False


class TestQuery:
    @pytest.mark.asyncio
    async def test_basic_query(self, provider):
        mock_response = _make_response(output_text="ChatGPT says hello")

        with patch("aiseo.providers.chatgpt.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.responses = AsyncMock()
            instance.responses.create = AsyncMock(return_value=mock_response)

            result = await provider.query("best project management tools")

        assert result.text == "ChatGPT says hello"
        assert result.model == "gpt-4o-mini"
        assert result.tokens_used == 100
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_query_extracts_citations(self, provider):
        annotations = [
            _make_annotation("url_citation", "https://example.com"),
            _make_annotation("url_citation", "https://other.com"),
        ]
        block = _make_block(annotations=annotations)
        output_item = _make_output_item(content=[block])
        mock_response = _make_response(
            output_text="Check these tools",
            output_items=[output_item],
        )

        with patch("aiseo.providers.chatgpt.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.responses = AsyncMock()
            instance.responses.create = AsyncMock(return_value=mock_response)

            result = await provider.query("best tools")

        assert result.citations == ["https://example.com", "https://other.com"]

    @pytest.mark.asyncio
    async def test_query_deduplicates_citations(self, provider):
        annotations = [
            _make_annotation("url_citation", "https://example.com"),
            _make_annotation("url_citation", "https://example.com"),
        ]
        block = _make_block(annotations=annotations)
        output_item = _make_output_item(content=[block])
        mock_response = _make_response(output_items=[output_item])

        with patch("aiseo.providers.chatgpt.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.responses = AsyncMock()
            instance.responses.create = AsyncMock(return_value=mock_response)

            result = await provider.query("test")

        assert result.citations == ["https://example.com"]

    @pytest.mark.asyncio
    async def test_query_handles_api_error(self, provider):
        from openai import APIError

        with patch("aiseo.providers.chatgpt.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.responses = AsyncMock()
            instance.responses.create = AsyncMock(
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
        with patch("aiseo.providers.chatgpt.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key=None)
            p = ChatGPTProvider()

            with pytest.raises(RuntimeError, match="not configured"):
                await p.query("test")

    @pytest.mark.asyncio
    async def test_query_handles_none_usage(self, provider):
        mock_response = _make_response()
        mock_response.usage = None

        with patch("aiseo.providers.chatgpt.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.responses = AsyncMock()
            instance.responses.create = AsyncMock(return_value=mock_response)

            result = await provider.query("test")

        assert result.tokens_used is None


class TestExtractCitations:
    def test_no_output_items(self):
        resp = SimpleNamespace(output=[])
        assert _extract_citations(resp) == []

    def test_output_item_without_content(self):
        resp = SimpleNamespace(output=[SimpleNamespace(content=None)])
        assert _extract_citations(resp) == []

    def test_block_without_annotations(self):
        block = SimpleNamespace(annotations=None)
        item = SimpleNamespace(content=[block])
        resp = SimpleNamespace(output=[item])
        assert _extract_citations(resp) == []

    def test_ignores_non_url_citation_annotations(self):
        ann = _make_annotation("file_citation", "https://skip.com")
        block = _make_block(annotations=[ann])
        item = _make_output_item(content=[block])
        resp = SimpleNamespace(output=[item])
        assert _extract_citations(resp) == []
