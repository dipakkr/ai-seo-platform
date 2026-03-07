"""Opportunities API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlmodel import Session, select

from aiseo.api.schemas import OpportunityResponse
from aiseo.models.base import get_session
from aiseo.models.opportunity import Opportunity
from aiseo.models.query import Query
from aiseo.models.scan import Scan

router = APIRouter(tags=["opportunities"])


@router.get(
    "/scans/{scan_id}/opportunities",
    response_model=list[OpportunityResponse],
)
def get_opportunities(
    scan_id: int,
    type: str | None = None,
    limit: int | None = None,
    session: Session = Depends(get_session),
):
    """Get opportunities for a scan, sorted by impact_score descending.

    Optional query parameters:
    - type: filter by opportunity_type (e.g. "invisible")
    - limit: max number of results to return
    """
    scan = session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    stmt = (
        select(Opportunity)
        .where(Opportunity.scan_id == scan_id)
        .order_by(Opportunity.impact_score.desc())
    )

    if type:
        stmt = stmt.where(Opportunity.opportunity_type == type)

    if limit is not None and limit > 0:
        stmt = stmt.limit(limit)

    opportunities = session.exec(stmt).all()

    # Fetch query texts in one query
    query_ids = {o.query_id for o in opportunities}
    query_map: dict[int, str] = {}
    if query_ids:
        queries = session.exec(select(Query).where(Query.id.in_(query_ids))).all()
        query_map = {q.id: q.text for q in queries}

    return [
        OpportunityResponse(
            id=o.id,
            scan_id=o.scan_id,
            query_id=o.query_id,
            query_text=query_map.get(o.query_id),
            opportunity_type=o.opportunity_type,
            impact_score=o.impact_score,
            visibility_gap=o.visibility_gap,
            competitors_visible=o.competitors_visible,
            providers_missing=o.providers_missing,
            recommendation=o.recommendation,
        )
        for o in opportunities
    ]
