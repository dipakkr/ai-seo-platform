"""Project CRUD API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from aiseo.api.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    QueryResponse,
)
from aiseo.models.base import get_session
from aiseo.models.project import Project
from aiseo.models.query import Query

logger = structlog.get_logger()

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_response(project: Project, queries: list[Query] | None = None) -> ProjectResponse:
    """Convert a Project ORM model to a ProjectResponse schema."""
    query_responses = []
    if queries is not None:
        query_responses = [
            QueryResponse(
                id=q.id,
                project_id=q.project_id,
                text=q.text,
                intent_category=q.intent_category,
                search_volume=q.search_volume,
                volume_source=q.volume_source,
                is_active=q.is_active,
            )
            for q in queries
        ]
    return ProjectResponse(
        id=project.id,
        url=project.url,
        brand_name=project.brand_name,
        brand_aliases=project.brand_aliases,
        description=project.description,
        category=project.category,
        competitors=project.competitors,
        features=project.features,
        target_audience=project.target_audience,
        created_at=project.created_at,
        updated_at=project.updated_at,
        queries=query_responses,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    session: Session = Depends(get_session),
):
    """Create a project from a URL.

    Calls brand_extractor to extract brand info, then query_generator
    to auto-generate buyer-intent queries.  Saves the Project and
    Query rows to the database and returns the full project.
    """
    from aiseo.services.brand_extractor import extract_brand_profile
    from aiseo.services.query_generator import generate_all_queries

    # Extract brand profile via LLM
    try:
        brand_profile = await extract_brand_profile(body.url)
    except Exception as exc:
        logger.error("brand_extraction_failed", url=body.url, error=str(exc))
        raise HTTPException(status_code=422, detail=f"Brand extraction failed: {exc}") from exc

    # Create the project
    now = datetime.now(timezone.utc)
    project = Project(
        url=body.url,
        brand_name=brand_profile.get("brand_name", ""),
        description=brand_profile.get("description", ""),
        category=brand_profile.get("category", ""),
        target_audience=brand_profile.get("target_audience", ""),
        created_at=now,
        updated_at=now,
    )
    project.brand_aliases = brand_profile.get("brand_aliases", [])
    project.competitors = brand_profile.get("competitors", [])
    project.features = brand_profile.get("features", [])

    session.add(project)
    session.commit()
    session.refresh(project)

    # Generate queries
    try:
        query_dicts = await generate_all_queries(brand_profile)
    except Exception as exc:
        logger.warning("query_generation_failed", error=str(exc))
        query_dicts = []

    queries: list[Query] = []
    for qd in query_dicts:
        q = Query(
            project_id=project.id,
            text=qd["text"],
            intent_category=qd.get("intent_category", "discovery"),
        )
        session.add(q)
        queries.append(q)

    session.commit()
    for q in queries:
        session.refresh(q)

    return _project_to_response(project, queries)


@router.get("", response_model=list[ProjectListResponse])
def list_projects(session: Session = Depends(get_session)):
    """List all projects."""
    projects = session.exec(select(Project).order_by(Project.created_at.desc())).all()
    return [
        ProjectListResponse(
            id=p.id,
            url=p.url,
            brand_name=p.brand_name,
            category=p.category,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, session: Session = Depends(get_session)):
    """Get a project by ID with its queries."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    queries = session.exec(
        select(Query).where(Query.project_id == project_id)
    ).all()

    return _project_to_response(project, queries)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    body: ProjectUpdateRequest,
    session: Session = Depends(get_session),
):
    """Update a project's brand profile fields."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = body.model_dump(exclude_unset=True)

    # Handle JSON list fields via their setters
    if "brand_aliases" in update_data:
        project.brand_aliases = update_data.pop("brand_aliases")
    if "competitors" in update_data:
        project.competitors = update_data.pop("competitors")
    if "features" in update_data:
        project.features = update_data.pop("features")

    # Handle simple scalar fields
    for field_name, value in update_data.items():
        setattr(project, field_name, value)

    project.updated_at = datetime.now(timezone.utc)
    session.add(project)
    session.commit()
    session.refresh(project)

    queries = session.exec(
        select(Query).where(Query.project_id == project_id)
    ).all()

    return _project_to_response(project, queries)
