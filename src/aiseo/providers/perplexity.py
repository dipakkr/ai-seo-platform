"""Perplexity Sonar provider using OpenAI-compatible API."""

import logging
import re
import time

from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aiseo.config import get_settings
from aiseo.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class PerplexityProvider(LLMProvider):
    """Perplexity Sonar API provider for AI search with citations."""

    name = "perplexity"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.perplexity_api_key

    def is_configured(self) -> bool:
        """Check if the Perplexity API key is set."""
        return self._api_key is not None and len(self._api_key) > 0

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=self._api_key,
            base_url="https://api.perplexity.ai",
        )

    @retry(
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query to Perplexity Sonar and return structured response."""
        if not self.is_configured():
            raise RuntimeError("Perplexity API key is not configured")

        client = self._get_client()
        start = time.perf_counter()

        try:
            response = await client.chat.completions.create(
                model="sonar",
                messages=[{"role": "user", "content": prompt}],
            )
        except (APIConnectionError, APITimeoutError, RateLimitError):
            raise
        except Exception:
            logger.exception("Perplexity API call failed")
            return LLMResponse(text="", citations=[], model="sonar", latency_ms=0)

        latency_ms = int((time.perf_counter() - start) * 1000)

        text = response.choices[0].message.content if response.choices else ""
        tokens_used = response.usage.total_tokens if response.usage else None
        citations = self._extract_citations(response, text)

        return LLMResponse(
            text=text or "",
            citations=citations,
            model="sonar",
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract_citations(response: object, text: str) -> list[str]:
        """Extract citation URLs from Perplexity response.

        Perplexity returns citations either as a top-level `citations` field
        on the response or inline as markdown links / numbered references.
        """
        urls: list[str] = []

        # Perplexity adds a `citations` list on the response object
        if hasattr(response, "citations") and response.citations:
            for url in response.citations:
                if isinstance(url, str):
                    urls.append(url)

        # Fallback: extract markdown-style URLs from the text
        if not urls and text:
            urls = re.findall(r'https?://[^\s\)\]>"]+', text)

        return list(dict.fromkeys(urls))  # dedupe preserving order
