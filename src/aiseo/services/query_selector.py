"""Smart query selection for scan runs.

Picks the most impactful queries to scan when the full list exceeds the
per-run limit.  Selection is based on:

  score = search_volume × intent_weight

where ``intent_weight`` reflects how likely a query type is to surface
brand mentions in AI responses:

  comparison    → 1.5   ("X vs Y" queries directly name brands)
  recommendation → 1.3  ("what do you recommend" → brand mentions)
  discovery     → 1.0   ("best X tools" → common, competitive)
  problem       → 0.8   (problem-aware; brands appear less often)

For queries that don't yet have a ``search_volume``, the autocomplete
adapter is called to estimate demand.  Fetched volumes are written back
to the DB so subsequent scans don't repeat the lookup.
"""

from __future__ import annotations

import asyncio
import logging

from sqlmodel import Session

from aiseo.models.query import Query

logger = logging.getLogger(__name__)

# Intent → multiplier (higher = more likely to return brand mentions)
INTENT_WEIGHTS: dict[str, float] = {
    "comparison": 1.5,
    "recommendation": 1.3,
    "discovery": 1.0,
    "problem": 0.8,
}

# Fallback volume when autocomplete also returns nothing
_DEFAULT_VOLUME = 10


def _score(query: Query) -> float:
    """Compute a priority score for a single query."""
    volume = query.search_volume if query.search_volume is not None else _DEFAULT_VOLUME
    weight = INTENT_WEIGHTS.get(query.intent_category, 1.0)
    return volume * weight


async def _fetch_and_save_volumes(
    queries: list[Query],
    engine,
) -> None:
    """Fetch autocomplete volumes for queries that don't have one yet.

    Volumes are persisted to the DB so the next scan reuses them.
    """
    missing = [q for q in queries if q.search_volume is None]
    if not missing:
        return

    try:
        from aiseo.volume.autocomplete import AutocompleteAdapter

        adapter = AutocompleteAdapter()
        volumes = await adapter.get_volumes([q.text for q in missing])
    except Exception:
        logger.warning("Autocomplete volume fetch failed; skipping.", exc_info=True)
        return

    with Session(engine) as session:
        for query in missing:
            vol = volumes.get(query.text)
            if vol is None:
                continue
            db_query = session.get(Query, query.id)
            if db_query is not None:
                db_query.search_volume = vol
                db_query.volume_source = "autocomplete"
                session.add(db_query)
                # Update the in-memory object so scoring below uses the new value
                query.search_volume = vol
        session.commit()

    logger.info(
        "Fetched autocomplete volumes for %d queries (out of %d missing)",
        sum(1 for q in missing if q.search_volume is not None),
        len(missing),
    )


async def select_queries(
    queries: list[Query],
    limit: int,
    engine,
) -> list[Query]:
    """Return the top ``limit`` queries ranked by search volume × intent weight.

    Side-effect: queries that were missing search volume will have their
    ``search_volume`` and ``volume_source`` fields updated in the DB.

    Args:
        queries: All active queries for the project.
        limit:   Maximum number to return.
        engine:  SQLAlchemy engine (used for DB writes).

    Returns:
        Up to ``limit`` queries, sorted by descending priority score.
    """
    if len(queries) <= limit:
        # Nothing to filter — still fetch volumes for future runs
        asyncio.ensure_future(_fetch_and_save_volumes(queries, engine))
        return queries

    # Fetch missing volumes before scoring so the ranking is meaningful
    await _fetch_and_save_volumes(queries, engine)

    ranked = sorted(queries, key=_score, reverse=True)
    selected = ranked[:limit]

    logger.info(
        "Query selector: %d total → top %d selected (scores %.0f … %.0f)",
        len(queries),
        len(selected),
        _score(selected[0]),
        _score(selected[-1]),
    )

    return selected
