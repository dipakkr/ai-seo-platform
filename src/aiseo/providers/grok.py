"""Grok provider using xAI API (OpenAI-compatible)."""

import logging
import time

from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from aiseo.config import get_request_api_key_override, get_settings
from aiseo.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_MODEL = "grok-3-mini"
_BASE_URL = "https://api.x.ai/v1"


class GrokProvider(LLMProvider):
    """xAI Grok provider (OpenAI-compatible API)."""

    name = "grok"

    def __init__(self) -> None:
        self._default_api_key = get_settings().xai_api_key

    def is_configured(self) -> bool:
        """Check if xAI API key is set."""
        api_key = get_request_api_key_override("xai_api_key") or self._default_api_key
        return bool(api_key)

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query to Grok and return structured response."""
        api_key = get_request_api_key_override("xai_api_key") or self._default_api_key
        if not api_key:
            raise RuntimeError("xAI API key is not configured")

        client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL)
        start_ms = _now_ms()

        try:
            response = await client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
        except RateLimitError:
            raise
        except APIError as exc:
            logger.error("xAI Grok API error for query %r: %s", prompt[:80], exc)
            return LLMResponse(
                text="",
                citations=[],
                model=_MODEL,
                tokens_used=None,
                latency_ms=_now_ms() - start_ms,
            )

        latency_ms = _now_ms() - start_ms
        text = ""
        if response.choices:
            text = response.choices[0].message.content or ""

        tokens_used = None
        if response.usage:
            tokens_used = response.usage.total_tokens

        return LLMResponse(
            text=text,
            citations=[],  # Grok chat API does not return citations
            model=_MODEL,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )


def _now_ms() -> int:
    return int(time.monotonic() * 1000)
