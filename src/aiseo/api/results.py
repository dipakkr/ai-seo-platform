"""Scan results API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlmodel import Session, select

from aiseo.api.schemas import ScanResultResponse
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

    if intent:
        # Need to join with Query to filter by intent_category
        stmt = stmt.join(Query, ScanResult.query_id == Query.id).where(
            Query.intent_category == intent
        )

    results = session.exec(stmt).all()

    return [
        ScanResultResponse(
            id=r.id,
            scan_id=r.scan_id,
            query_id=r.query_id,
            provider=r.provider,
            raw_response=r.raw_response,
            brand_mentioned=r.brand_mentioned,
            brand_position=r.brand_position,
            brand_sentiment=r.brand_sentiment,
            brand_context=r.brand_context,
            competitors_mentioned=r.competitors_mentioned,
            citations=r.citations,
            brand_cited=r.brand_cited,
            response_tokens=r.response_tokens,
            latency_ms=r.latency_ms,
        )
        for r in results
    ]
