"""Rank visibility gaps by impact and generate recommendations."""

import json
import logging
from collections import defaultdict

from sqlmodel import Session, select

from aiseo.models.base import get_engine
from aiseo.models.opportunity import Opportunity
from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.result import ScanResult

logger = logging.getLogger(__name__)

RECOMMENDATIONS = {
    "invisible": (
        "Your brand is invisible for '{query}' across {providers}. "
        "Competitors like {competitors} are being recommended instead. "
        "Consider: create a dedicated page targeting this query, "
        "get listed in comparison articles, ensure structured data coverage."
    ),
    "competitor_dominated": (
        "You appear for '{query}' but {competitors} are recommended first. "
        "Strengthen your positioning by adding statistics, citations, "
        "and comparison content on your site."
    ),
    "partial_visibility": (
        "You're visible on {visible_providers} but missing from {missing_providers}. "
        "Check that your content is indexed by the missing platforms. "
        "Ensure Bing indexing (ChatGPT relies on Bing)."
    ),
    "negative_sentiment": (
        "Your brand is mentioned for '{query}' but in a negative context. "
        "Review the AI's sources and address any outdated/inaccurate information."
    ),
}


def compute_opportunities(
    scan_id: int, project_id: int, *, engine=None
) -> list[Opportunity]:
    """Compute and persist ranked opportunities for a scan.

    For each query, classifies the opportunity type based on brand vs
    competitor visibility, calculates an impact score (search_volume x
    visibility_gap), generates a recommendation, and saves Opportunity
    rows to the database.

    Args:
        scan_id: The scan to analyse.
        project_id: The project that owns the scan.
        engine: Optional SQLAlchemy engine (for testing).

    Returns:
        Opportunities sorted by impact_score descending.
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        project = session.get(Project, project_id)
        if project is None:
            logger.error("Project %d not found", project_id)
            return []

        # Load all results joined with queries
        stmt = (
            select(ScanResult, Query)
            .join(Query, ScanResult.query_id == Query.id)
            .where(ScanResult.scan_id == scan_id)
        )
        rows = session.exec(stmt).all()

        if not rows:
            logger.warning("No results for scan %d", scan_id)
            return []

        # Group results by query_id
        by_query: dict[int, list[tuple[ScanResult, Query]]] = defaultdict(list)
        for result, query in rows:
            by_query[query.id].append((result, query))

        # All providers that participated in this scan
        all_providers = {r.provider for r, _ in rows}

        opportunities: list[Opportunity] = []

        for query_id, result_pairs in by_query.items():
            query = result_pairs[0][1]
            volume = query.search_volume if query.search_volume else 1

            # Analyse brand visibility across providers
            providers_mentioned: list[str] = []
            providers_not_mentioned: list[str] = []
            best_brand_position: int | None = None
            has_negative = False
            all_competitors: set[str] = set()

            for result, _ in result_pairs:
                if result.brand_mentioned:
                    providers_mentioned.append(result.provider)
                    if result.brand_position is not None:
                        if best_brand_position is None or result.brand_position < best_brand_position:
                            best_brand_position = result.brand_position
                    if result.brand_sentiment == "negative":
                        has_negative = True
                else:
                    providers_not_mentioned.append(result.provider)

                for comp in result.competitors_mentioned:
                    all_competitors.add(comp)

            # Also count providers that didn't return a result for this query
            providers_in_results = {r.provider for r, _ in result_pairs}
            for p in all_providers - providers_in_results:
                providers_not_mentioned.append(p)

            competitors_list = sorted(all_competitors)

            # Classify opportunity type
            opp_type = _classify(
                providers_mentioned,
                providers_not_mentioned,
                competitors_list,
                best_brand_position,
                has_negative,
                all_providers,
            )

            if opp_type is None:
                continue  # No opportunity — brand is well-positioned

            # Visibility gap: fraction of providers where brand is NOT visible
            # weighted by competitor presence
            brand_visibility = len(providers_mentioned) / len(all_providers) if all_providers else 0.0
            competitor_visibility = _competitor_visibility(result_pairs, all_providers)
            visibility_gap = max(0.0, competitor_visibility - brand_visibility)

            # For negative sentiment, use a fixed gap
            if opp_type == "negative_sentiment":
                visibility_gap = max(visibility_gap, 0.3)

            impact_score = volume * visibility_gap

            recommendation = _build_recommendation(
                opp_type,
                query.text,
                competitors_list,
                providers_mentioned,
                providers_not_mentioned,
            )

            opp = Opportunity(
                scan_id=scan_id,
                query_id=query_id,
                opportunity_type=opp_type,
                impact_score=round(impact_score, 2),
                visibility_gap=round(visibility_gap, 3),
                recommendation=recommendation,
            )
            opp.competitors_visible = competitors_list
            opp.providers_missing = providers_not_mentioned
            session.add(opp)
            opportunities.append(opp)

        session.commit()

        # Refresh to get IDs
        for opp in opportunities:
            session.refresh(opp)

    opportunities.sort(key=lambda o: o.impact_score, reverse=True)
    return opportunities


def _classify(
    mentioned: list[str],
    not_mentioned: list[str],
    competitors: list[str],
    best_position: int | None,
    has_negative: bool,
    all_providers: set[str],
) -> str | None:
    """Classify the opportunity type for a single query."""
    if not mentioned and competitors:
        return "invisible"
    if has_negative:
        return "negative_sentiment"
    if mentioned and not_mentioned:
        return "partial_visibility"
    if mentioned and competitors and best_position is not None and best_position > 1:
        return "competitor_dominated"
    # No clear opportunity
    return None


def _competitor_visibility(
    result_pairs: list[tuple[ScanResult, Query]],
    all_providers: set[str],
) -> float:
    """Fraction of providers where at least one competitor is mentioned."""
    if not all_providers:
        return 0.0
    providers_with_competitors = set()
    for result, _ in result_pairs:
        if result.competitors_mentioned:
            providers_with_competitors.add(result.provider)
    return len(providers_with_competitors) / len(all_providers)


def _build_recommendation(
    opp_type: str,
    query_text: str,
    competitors: list[str],
    visible_providers: list[str],
    missing_providers: list[str],
) -> str:
    """Fill in the recommendation template for the opportunity type."""
    template = RECOMMENDATIONS.get(opp_type, "")
    competitors_str = ", ".join(competitors[:3]) if competitors else "other brands"
    return template.format(
        query=query_text,
        competitors=competitors_str,
        providers=", ".join(missing_providers) if missing_providers else "all providers",
        visible_providers=", ".join(visible_providers) if visible_providers else "none",
        missing_providers=", ".join(missing_providers) if missing_providers else "none",
    )
