"""Google Ads Keyword Planner search volume adapter."""

import logging

from aiseo.config import get_settings
from aiseo.volume.base import SearchVolumeAdapter

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200


class GoogleAdsAdapter(SearchVolumeAdapter):
    """Fetch exact monthly search volumes from Google Keyword Planner API.

    Requires the ``google-ads`` package and valid OAuth credentials.
    """

    name = "google_ads"

    def __init__(self) -> None:
        settings = get_settings()
        self._developer_token = settings.google_ads_developer_token
        self._client_id = settings.google_ads_client_id

    def is_configured(self) -> bool:
        """Check that required Google Ads credentials are present."""
        return bool(self._developer_token) and bool(self._client_id)

    async def get_volumes(self, keywords: list[str]) -> dict[str, int | None]:
        """Fetch volumes in batches of 200 (Keyword Planner API limit)."""
        if not self.is_configured():
            logger.warning("Google Ads adapter is not configured; returning None for all keywords")
            return {kw: None for kw in keywords}

        results: dict[str, int | None] = {}
        for i in range(0, len(keywords), _BATCH_SIZE):
            batch = keywords[i : i + _BATCH_SIZE]
            batch_results = await self._fetch_batch(batch)
            results.update(batch_results)
        return results

    async def _fetch_batch(self, keywords: list[str]) -> dict[str, int | None]:
        """Fetch a single batch of up to 200 keywords.

        TODO: Implement using the google-ads Python client library.
        Rough steps:
            1. Build a GoogleAdsClient from credentials (developer_token,
               client_id, client_secret, refresh_token, login_customer_id).
            2. Use KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics
               or KeywordPlanIdeaService.GenerateKeywordIdeas.
            3. Map each keyword to its avg_monthly_searches value.

        Example (pseudocode):
            from google.ads.googleads.client import GoogleAdsClient
            ga_client = GoogleAdsClient.load_from_dict(credentials)
            service = ga_client.get_service("KeywordPlanIdeaService")
            request = ga_client.get_type("GenerateKeywordIdeasRequest")
            request.customer_id = customer_id
            request.keyword_seed.keywords.extend(keywords)
            response = service.generate_keyword_ideas(request=request)
            return {idea.text: idea.keyword_idea_metrics.avg_monthly_searches
                    for idea in response.results}
        """
        logger.info("Google Ads batch fetch not yet implemented; returning None for %d keywords", len(keywords))
        return {kw: None for kw in keywords}
