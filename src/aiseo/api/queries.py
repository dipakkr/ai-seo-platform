"""Query management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from aiseo.api.schemas import QueryCreateRequest, QueryResponse, QueryUpdateRequest
from aiseo.models.base import get_session
from aiseo.models.project import Project
from aiseo.models.query import Query

router = APIRouter(tags=["queries"])


@router.post(
    "/projects/{project_id}/queries",
    response_model=QueryResponse,
    status_code=201,
)
def add_query(
    project_id: int,
    body: QueryCreateRequest,
    session: Session = Depends(get_session),
):
    """Add a custom query to a project."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    query = Query(
        project_id=project_id,
        text=body.text,
        intent_category=body.intent_category,
        search_volume=body.search_volume,
        volume_source="csv" if body.search_volume is not None else None,
        is_active=True,
    )
    session.add(query)
    session.commit()
    session.refresh(query)

    return QueryResponse(
        id=query.id,
        project_id=query.project_id,
        text=query.text,
        intent_category=query.intent_category,
        search_volume=query.search_volume,
        volume_source=query.volume_source,
        is_active=query.is_active,
    )


@router.patch("/queries/{query_id}", response_model=QueryResponse)
def update_query(
    query_id: int,
    body: QueryUpdateRequest,
    session: Session = Depends(get_session),
):
    """Update a query's text, intent category, or active status."""
    query = session.get(Query, query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")

    if body.text is not None:
        query.text = body.text
    if body.intent_category is not None:
        query.intent_category = body.intent_category
    if body.search_volume is not None:
        query.search_volume = body.search_volume
        query.volume_source = "csv"
    if body.is_active is not None:
        query.is_active = body.is_active

    session.add(query)
    session.commit()
    session.refresh(query)

    return QueryResponse(
        id=query.id,
        project_id=query.project_id,
        text=query.text,
        intent_category=query.intent_category,
        search_volume=query.search_volume,
        volume_source=query.volume_source,
        is_active=query.is_active,
    )


@router.delete("/queries/{query_id}", status_code=204)
def delete_query(
    query_id: int,
    session: Session = Depends(get_session),
):
    """Delete a query."""
    query = session.get(Query, query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")

    session.delete(query)
    session.commit()
