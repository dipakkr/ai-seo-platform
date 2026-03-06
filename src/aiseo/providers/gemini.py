"""Gemini provider using Google GenAI with search grounding."""

import time
import logging

from google import genai
from google.genai import types as genai_types
from google.genai.errors import APIError, ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from aiseo.config import get_settings
from aiseo.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.0-flash"


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Check if the exception is a rate-limit (429) error."""
    return isinstance(exc, ClientError) and getattr(exc, "code", None) == 429


class GeminiProvider(LLMProvider):
    """Google Gemini provider with search grounding."""

    name = "gemini"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.google_api_key

    def is_configured(self) -> bool:
        """Check if Google API key is set."""
        return self._api_key is not None and len(self._api_key) > 0

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query to Gemini with search grounding and return structured response."""
        if not self.is_configured():
            raise RuntimeError("Google API key is not configured")

        client = genai.Client(api_key=self._api_key)
        start_ms = _now_ms()

        try:
            response = await client.aio.models.generate_content(
                model=_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    tools=[
                        genai_types.Tool(
                            google_search=genai_types.GoogleSearchRetrieval()
                        )
                    ]
                ),
            )
        except ClientError as exc:
            if exc.code == 429:
                raise
            logger.error("Gemini API error for query %r: %s", prompt[:80], exc)
            return LLMResponse(
                text="",
                citations=[],
                model=_MODEL,
                tokens_used=None,
                latency_ms=_now_ms() - start_ms,
            )
        except APIError as exc:
            logger.error("Gemini API error for query %r: %s", prompt[:80], exc)
            return LLMResponse(
                text="",
                citations=[],
                model=_MODEL,
                tokens_used=None,
                latency_ms=_now_ms() - start_ms,
            )

        latency_ms = _now_ms() - start_ms
        text = response.text or ""
        citations = _extract_citations(response)

        tokens_used = None
        if response.usage_metadata:
            tokens_used = getattr(response.usage_metadata, "total_token_count", None)

        return LLMResponse(
            text=text,
            citations=citations,
            model=_MODEL,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )


def _extract_citations(response) -> list[str]:
    """Extract unique URLs from grounding metadata in the response."""
    urls: list[str] = []
    try:
        candidates = response.candidates or []
        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue
            chunks = getattr(metadata, "grounding_chunks", None)
            if not chunks:
                continue
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web:
                    uri = getattr(web, "uri", None)
                    if uri and uri not in urls:
                        urls.append(uri)
    except Exception:
        logger.debug("Failed to extract grounding citations", exc_info=True)
    return urls


def _now_ms() -> int:
    return int(time.monotonic() * 1000)
