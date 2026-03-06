"""Compute AI Visibility Score (0-100) from scan results."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from sqlmodel import Session, select

from aiseo.models.base import get_engine
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan

logger = logging.getLogger(__name__)

POSITION_BONUS = {1: 1.0, 2: 0.7, 3: 0.5}
DEFAULT_POSITION_BONUS = 0.3  # position 4+
CITATION_BONUS = 0.2
SENTIMENT_MODIFIER = {"positive": 1.0, "neutral": 0.7, "negative": 0.3}
DEFAULT_SENTIMENT = 0.7  # treat None as neutral
MAX_QUERY_SCORE = (1.0 + CITATION_BONUS) * 1.0  # mention=1, pos=1, cited, positive


@dataclass
class VisibilityScore:
    """AI Visibility Score breakdown."""

    overall: float = 0.0
    per_llm: dict[str, float] = field(default_factory=dict)
    per_category: dict[str, float] = field(default_factory=dict)
    competitor_scores: dict[str, float] = field(default_factory=dict)


def score_single_result(result: ScanResult) -> float:
    """Score a single ScanResult using the scoring formula.

    Returns raw score (not normalized to 0-100).
    """
    if not result.brand_mentioned:
        return 0.0

    pos = result.brand_position
    if pos is None:
        position_bonus = 0.0
    elif pos <= 0:
        position_bonus = 0.0
    elif pos <= 3:
        position_bonus = POSITION_BONUS[pos]
    else:
        position_bonus = DEFAULT_POSITION_BONUS

    citation_bonus = CITATION_BONUS if result.brand_cited else 0.0
    sentiment = SENTIMENT_MODIFIER.get(
        result.brand_sentiment or "", DEFAULT_SENTIMENT
    )

    return 1.0 * (position_bonus + citation_bonus) * sentiment


def _weighted_average(
    scores: list[float], weights: list[float]
) -> float:
    """Compute weighted average, returns 0.0 if no weights."""
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def compute_visibility_score(
    scan_id: int, *, engine=None
) -> VisibilityScore:
    """Compute the AI Visibility Score for a completed scan.

    Loads all ScanResults for the scan, joins with Query for metadata,
    computes overall/per-LLM/per-category/competitor scores, and updates
    the Scan row in the database.

    Args:
        scan_id: The scan to score.
        engine: Optional SQLAlchemy engine (for testing). Uses default if None.

    Returns:
        VisibilityScore with all breakdowns.
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        # Load all results joined with their queries
        stmt = (
            select(ScanResult, Query)
            .join(Query, ScanResult.query_id == Query.id)
            .where(ScanResult.scan_id == scan_id)
        )
        rows = session.exec(stmt).all()

        if not rows:
            logger.warning("No results found for scan_id=%d", scan_id)
            _update_scan_score(session, scan_id, 0.0)
            return VisibilityScore()

        # Compute per-result scores and group by dimensions
        all_scores: list[float] = []
        all_weights: list[float] = []
        llm_groups: dict[str, tuple[list[float], list[float]]] = defaultdict(
            lambda: ([], [])
        )
        cat_groups: dict[str, tuple[list[float], list[float]]] = defaultdict(
            lambda: ([], [])
        )
        competitor_counts: dict[str, int] = defaultdict(int)
        unique_query_ids: set[int] = set()

        for result, query in rows:
            score = score_single_result(result)
            weight = query.search_volume if query.search_volume else 1.0

            # Normalize to 0-100 scale per result
            normalized = (score / MAX_QUERY_SCORE) * 100.0 if MAX_QUERY_SCORE > 0 else 0.0

            all_scores.append(normalized)
            all_weights.append(weight)

            llm_scores, llm_weights = llm_groups[result.provider]
            llm_scores.append(normalized)
            llm_weights.append(weight)

            cat_scores, cat_weights = cat_groups[query.intent_category]
            cat_scores.append(normalized)
            cat_weights.append(weight)

            # Track competitors and unique queries
            unique_query_ids.add(query.id)
            for comp in result.competitors_mentioned:
                competitor_counts[comp] += 1

        overall = _weighted_average(all_scores, all_weights)

        per_llm = {
            provider: _weighted_average(scores, weights)
            for provider, (scores, weights) in sorted(llm_groups.items())
        }

        per_category = {
            cat: _weighted_average(scores, weights)
            for cat, (scores, weights) in sorted(cat_groups.items())
        }

        # Competitor scores: percentage of total result rows where competitor appears
        total_results = len(rows)
        competitor_scores = {
            comp: round((count / total_results) * 100.0, 1)
            for comp, count in sorted(
                competitor_counts.items(), key=lambda x: -x[1]
            )
        }

        overall = round(overall, 1)
        per_llm = {k: round(v, 1) for k, v in per_llm.items()}
        per_category = {k: round(v, 1) for k, v in per_category.items()}

        _update_scan_score(session, scan_id, overall)

        return VisibilityScore(
            overall=overall,
            per_llm=per_llm,
            per_category=per_category,
            competitor_scores=competitor_scores,
        )


def _update_scan_score(session: Session, scan_id: int, score: float) -> None:
    """Update the visibility_score field on the Scan row."""
    scan = session.get(Scan, scan_id)
    if scan:
        scan.visibility_score = score
        session.add(scan)
        session.commit()
