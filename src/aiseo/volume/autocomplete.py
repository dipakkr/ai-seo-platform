"""Free autocomplete-based search volume proxy."""

import asyncio
import logging

import httpx

from aiseo.volume.base import SearchVolumeAdapter

logger = logging.getLogger(__name__)

# Scale factor: map suggestion count (0-10) to estimated monthly volume.
# Google autocomplete returns up to 10 suggestions; more suggestions implies
# higher search demand.  These are rough proxies, not exact volumes.
_VOLUME_SCALE = {
    0: 0,
    1: 10,
    2: 50,
    3: 100,
    4: 200,
    5: 500,
    6: 1000,
    7: 2000,
    8: 5000,
    9: 8000,
    10: 10000,
}


class AutocompleteAdapter(SearchVolumeAdapter):
    """Estimate relative search demand via Google autocomplete suggestion count."""

    name = "autocomplete"

    _BASE_URL = "https://suggestqueries.google.com/complete/search"

    def __init__(self, max_concurrent: int = 5) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def get_volumes(self, keywords: list[str]) -> dict[str, int | None]:
        """Fetch suggestion counts for all keywords concurrently."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [self._fetch_one(client, kw) for kw in keywords]
            results = await asyncio.gather(*tasks)
        return dict(zip(keywords, results))

    async def _fetch_one(self, client: httpx.AsyncClient, keyword: str) -> int | None:
        """Get estimated volume for a single keyword."""
        async with self._semaphore:
            try:
                resp = await client.get(
                    self._BASE_URL,
                    params={"client": "firefox", "q": keyword},
                )
                resp.raise_for_status()
                data = resp.json()
                # Response format: ["query", ["suggestion1", "suggestion2", ...]]
                suggestions = data[1] if len(data) > 1 else []
                count = min(len(suggestions), 10)
                return _VOLUME_SCALE.get(count, 0)
            except Exception:
                logger.warning("Autocomplete lookup failed for %r", keyword, exc_info=True)
                return None
