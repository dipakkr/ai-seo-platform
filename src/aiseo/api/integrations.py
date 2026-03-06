"""Integration management API routes."""

from __future__ import annotations

from fastapi import APIRouter

from aiseo.api.schemas import IntegrationTestRequest, IntegrationTestResponse
from aiseo.providers.base import LLMProvider

router = APIRouter(tags=["integrations"])


def _provider_from_name(name: str) -> LLMProvider | None:
    provider_name = name.strip().lower()

    if provider_name == "chatgpt":
        from aiseo.providers.chatgpt import ChatGPTProvider

        return ChatGPTProvider()
    if provider_name == "perplexity":
        from aiseo.providers.perplexity import PerplexityProvider

        return PerplexityProvider()
    if provider_name == "gemini":
        from aiseo.providers.gemini import GeminiProvider

        return GeminiProvider()
    if provider_name == "claude":
        from aiseo.providers.claude import ClaudeProvider

        return ClaudeProvider()

    return None


@router.post("/integrations/test", response_model=IntegrationTestResponse)
async def test_integration(body: IntegrationTestRequest):
    """Test whether a provider key works for the current request context."""
    provider = _provider_from_name(body.provider)
    if provider is None:
        return IntegrationTestResponse(
            provider=body.provider,
            configured=False,
            success=False,
            error="Unknown provider",
        )

    if not provider.is_configured():
        return IntegrationTestResponse(
            provider=provider.name,
            configured=False,
            success=False,
            error="API key not configured",
        )

    try:
        response = await provider.query("Reply with exactly: OK")
        return IntegrationTestResponse(
            provider=provider.name,
            configured=True,
            success=True,
            model=response.model or None,
            latency_ms=response.latency_ms,
        )
    except Exception as exc:
        return IntegrationTestResponse(
            provider=provider.name,
            configured=True,
            success=False,
            error=str(exc),
        )
