"""Abstract base class for search volume adapters."""

from abc import ABC, abstractmethod


class SearchVolumeAdapter(ABC):
    """Base class for search volume data sources."""

    name: str

    @abstractmethod
    async def get_volumes(self, keywords: list[str]) -> dict[str, int | None]:
        """Return {keyword: monthly_search_volume} for each keyword."""
