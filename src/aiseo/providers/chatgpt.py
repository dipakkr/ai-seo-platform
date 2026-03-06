"""ChatGPT provider using OpenAI Responses API with web_search."""

import time
import logging

from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from aiseo.config import get_settings
from aiseo.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ChatGPTProvider(LLMProvider):
    """OpenAI ChatGPT provider with web search grounding."""

    name = "chatgpt"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key

    def is_configured(self) -> bool:
        """Check if OpenAI API key is set."""
        return self._api_key is not None and len(self._api_key) > 0

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query to ChatGPT with web search and return structured response."""
        if not self.is_configured():
            raise RuntimeError("OpenAI API key is not configured")

        client = AsyncOpenAI(api_key=self._api_key)
        start_ms = _now_ms()

        try:
            response = await client.responses.create(
                model="gpt-4o-mini",
                tools=[{"type": "web_search"}],
                input=prompt,
            )
        except RateLimitError:
            raise
        except APIError as exc:
            logger.error("OpenAI API error for query %r: %s", prompt[:80], exc)
            return LLMResponse(
                text="",
                citations=[],
                model="gpt-4o-mini",
                tokens_used=None,
                latency_ms=_now_ms() - start_ms,
            )

        latency_ms = _now_ms() - start_ms
        text = response.output_text or ""

        citations = _extract_citations(response)

        tokens_used = None
        if response.usage:
            tokens_used = response.usage.total_tokens

        return LLMResponse(
            text=text,
            citations=citations,
            model="gpt-4o-mini",
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )


def _extract_citations(response) -> list[str]:
    """Extract unique URLs from url_citation annotations in the response."""
    urls: list[str] = []
    for item in response.output:
        content = getattr(item, "content", None)
        if not content:
            continue
        for block in content:
            annotations = getattr(block, "annotations", None)
            if not annotations:
                continue
            for ann in annotations:
                if getattr(ann, "type", None) == "url_citation":
                    url = getattr(ann, "url", None)
                    if url and url not in urls:
                        urls.append(url)
    return urls


def _now_ms() -> int:
    return int(time.monotonic() * 1000)
