"""Scan results API routes."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from aiseo.api.schemas import (
    AggregatedBrandRank,
    BrandRankingEntry,
    QueryRankingsResponse,
    ScanResultResponse,
)
from aiseo.models.base import get_session
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan

router = APIRouter(tags=["results"])


@router.get("/scans/{scan_id}/results", response_model=list[ScanResultResponse])
def get_scan_results(
    scan_id: int,
    provider: str | None = None,
    intent: str | None = None,
    query_id: int | None = None,
    session: Session = Depends(get_session),
):
    """Get all ScanResult rows for a scan.

    Optional query parameters:
    - provider: filter by LLM provider (e.g. "chatgpt")
    - intent: filter by query intent category (e.g. "discovery")
    """
    scan = session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    stmt = select(ScanResult).where(ScanResult.scan_id == scan_id)

    if provider:
        stmt = stmt.where(ScanResult.provider == provider)

    if query_id is not None:
        stmt = stmt.where(ScanResult.query_id == query_id)

    if intent:
        # Need to join with Query to filter by intent_category
        stmt = stmt.join(Query, ScanResult.query_id == Query.id).where(
            Query.intent_category == intent
        )

    results = session.exec(stmt).all()
    query_ids = {r.query_id for r in results}
    query_map: dict[int, Query] = {}
    if query_ids:
        queries = session.exec(select(Query).where(Query.id.in_(query_ids))).all()
        query_map = {q.id: q for q in queries}

    return [
        ScanResultResponse(
            id=r.id,
            scan_id=r.scan_id,
            query_id=r.query_id,
            query_text=query_map.get(r.query_id).text if query_map.get(r.query_id) else None,
            provider=r.provider,
            raw_response=r.raw_response,
            brand_mentioned=r.brand_mentioned,
            brand_position=r.brand_position,
            brand_sentiment=r.brand_sentiment,
            brand_context=r.brand_context,
            competitors_mentioned=r.competitors_mentioned,
            citations=r.citations,
            brand_cited=r.brand_cited,
            brands_ranked=[BrandRankingEntry(**b) for b in r.brands_ranked],
            response_tokens=r.response_tokens,
            latency_ms=r.latency_ms,
        )
        for r in results
    ]


@router.get("/scans/{scan_id}/rankings", response_model=list[QueryRankingsResponse])
def get_scan_rankings(
    scan_id: int,
    session: Session = Depends(get_session),
):
    """Get per-query aggregated brand rankings for a scan."""
    scan = session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    results = session.exec(
        select(ScanResult).where(ScanResult.scan_id == scan_id)
    ).all()
    if not results:
        return []

    query_ids = sorted({r.query_id for r in results})
    queries = session.exec(
        select(Query).where(Query.id.in_(query_ids))
    ).all()
    query_map = {q.id: q for q in queries}

    results_by_query: dict[int, list[ScanResult]] = defaultdict(list)
    for result in results:
        results_by_query[result.query_id].append(result)

    responses: list[QueryRankingsResponse] = []
    for query_id in query_ids:
        q = query_map.get(query_id)
        if q is None:
            continue

        per_provider: dict[str, list[BrandRankingEntry]] = {}
        aggregates: dict[str, dict] = {}

        for result in results_by_query.get(query_id, []):
            brands = [BrandRankingEntry(**b) for b in result.brands_ranked]
            brands.sort(key=lambda b: b.position if b.position is not None else 9999)
            per_provider[result.provider] = brands

            provider_seen: set[str] = set()
            for brand in brands:
                key = brand.name.lower().strip()
                if not key:
                    continue

                agg = aggregates.setdefault(
                    key,
                    {
                        "name": brand.name,
                        "positions": [],
                        "providers": set(),
                        "is_your_brand": False,
                    },
                )
                if not agg["name"] and brand.name:
                    agg["name"] = brand.name
                if brand.position is not None:
                    agg["positions"].append(brand.position)
                if key not in provider_seen:
                    agg["providers"].add(result.provider)
                    provider_seen.add(key)
                agg["is_your_brand"] = agg["is_your_brand"] or brand.is_your_brand

        aggregated_ranks: list[AggregatedBrandRank] = []
        for agg in aggregates.values():
            if agg["positions"]:
                avg_position = round(sum(agg["positions"]) / len(agg["positions"]), 2)
            else:
                # Mentioned in prose only (no ranked position in parsed lists).
                avg_position = 999.0
            providers = sorted(agg["providers"])
            aggregated_ranks.append(
                AggregatedBrandRank(
                    name=agg["name"],
                    avg_position=avg_position,
                    mention_count=len(providers),
                    providers=providers,
                    is_your_brand=agg["is_your_brand"],
                )
            )

        aggregated_ranks.sort(key=lambda r: (r.avg_position, -r.mention_count, r.name.lower()))

        responses.append(
            QueryRankingsResponse(
                query_id=q.id,
                query_text=q.text,
                intent_category=q.intent_category,
                search_volume=q.search_volume,
                rankings=aggregated_ranks[:10],
                per_provider=per_provider,
            )
        )

    return responses
