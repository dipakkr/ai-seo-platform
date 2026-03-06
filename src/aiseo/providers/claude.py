"""Claude provider using Anthropic Messages API (no web search)."""

import logging
import time

from anthropic import AsyncAnthropic, APIError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from aiseo.config import get_request_api_key_override, get_settings
from aiseo.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider. No web search — checks training data presence."""

    name = "claude"

    def __init__(self) -> None:
        self._default_api_key = get_settings().anthropic_api_key

    def is_configured(self) -> bool:
        """Check if Anthropic API key is set."""
        return bool(get_request_api_key_override("anthropic_api_key") or self._default_api_key)

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query to Claude and return structured response."""
        api_key = get_request_api_key_override("anthropic_api_key") or self._default_api_key
        if not api_key:
            raise RuntimeError("Anthropic API key is not configured")

        client = AsyncAnthropic(api_key=api_key)
        start_ms = _now_ms()

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except RateLimitError:
            raise
        except APIError as exc:
            logger.error("Anthropic API error for query %r: %s", prompt[:80], exc)
            return LLMResponse(
                text="",
                citations=[],
                model="claude-sonnet-4-20250514",
                tokens_used=None,
                latency_ms=_now_ms() - start_ms,
            )

        latency_ms = _now_ms() - start_ms
        text = response.content[0].text if response.content else ""

        tokens_used = None
        if response.usage:
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return LLMResponse(
            text=text,
            citations=[],
            model="claude-sonnet-4-20250514",
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )


def _now_ms() -> int:
    return int(time.monotonic() * 1000)
