"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    text: str
    citations: list[str] = field(default_factory=list)
    model: str = ""
    tokens_used: int | None = None
    latency_ms: int = 0


class LLMProvider(ABC):
    """Base class for LLM provider integrations."""

    name: str

    @abstractmethod
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query and return structured response."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API key is set."""
