"""Scan management API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from aiseo.api.schemas import (
    ScanRequest,
    ScanResponse,
    ScanTriggerResponse,
    SingleQueryResultResponse,
    SingleQueryScanResponse,
)
from aiseo.config import get_request_api_key_override
from aiseo.models.base import get_session
from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.scan import Scan

logger = structlog.get_logger()

router = APIRouter(tags=["scans"])
DEMO_SCAN_QUERY_LIMIT = 10


def _redis_available() -> bool:
    """Check if Redis is reachable for Celery task dispatch."""
    try:
        from aiseo.config import get_settings
        import redis

        settings = get_settings()
        r = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def _has_request_api_key_overrides() -> bool:
    """Check whether API keys were supplied on this request via headers."""
    return any(
        get_request_api_key_override(name)
        for name in (
            "openai_api_key",
            "anthropic_api_key",
            "google_api_key",
            "perplexity_api_key",
            "xai_api_key",
        )
    )


@router.post(
    "/projects/{project_id}/scan",
    response_model=ScanTriggerResponse,
    status_code=202,
)
async def trigger_scan(
    project_id: int,
    body: ScanRequest = ScanRequest(),
    session: Session = Depends(get_session),
):
    """Trigger a new visibility scan for a project.

    Creates a Scan row, then attempts to dispatch a Celery task.
    If Celery/Redis is unavailable, falls back to running the scan
    synchronously.
    """
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify there are active queries
    active_queries = session.exec(
        select(Query).where(Query.project_id == project_id, Query.is_active == True)  # noqa: E712
    ).all()
    if len(active_queries) == 0:
        raise HTTPException(
            status_code=400,
            detail="No active queries for this project. Add queries first.",
        )

    # Use limit as an estimate; the scanner will update total_queries once
    # smart query selection has run and the exact count is known.
    estimated_count = min(len(active_queries), DEMO_SCAN_QUERY_LIMIT)

    # Create scan record
    scan = Scan(project_id=project_id, status="pending", total_queries=estimated_count)
    session.add(scan)
    session.commit()
    session.refresh(scan)
    scan_id = scan.id

    # Try Celery dispatch only if Redis is available
    if _redis_available() and not _has_request_api_key_overrides():
        try:
            from aiseo.tasks.scan_task import run_scan_task

            run_scan_task.delay(project_id, scan_id, body.providers)
            return ScanTriggerResponse(
                scan_id=scan_id,
                status="pending",
                message="Scan dispatched to background worker.",
            )
        except Exception:
            logger.warning(
                "celery_dispatch_failed",
                scan_id=scan_id,
                msg="Falling back to synchronous scan.",
            )

    # Fallback: run synchronously
    logger.info("running_scan_sync", scan_id=scan_id)
    try:
        from aiseo.services.visibility_scanner import run_scan
        from aiseo.services.scorer import compute_visibility_score
        from aiseo.services.opportunity_engine import compute_opportunities

        await run_scan(project_id, scan_id, allowed_providers=body.providers)

        try:
            compute_visibility_score(scan_id)
        except Exception:
            logger.exception("scorer_failed", scan_id=scan_id)

        try:
            compute_opportunities(scan_id, project_id)
        except Exception:
            logger.exception("opportunity_engine_failed", scan_id=scan_id)

        return ScanTriggerResponse(
            scan_id=scan_id,
            status="completed",
            message="Scan completed synchronously.",
        )
    except Exception as exc:
        logger.exception("sync_scan_failed", scan_id=scan_id)
        # Mark the scan as failed in DB
        scan = session.get(Scan, scan_id)
        if scan is not None:
            scan.status = "failed"
            scan.error_message = str(exc)
            session.add(scan)
            session.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {exc}",
        ) from exc


@router.get("/scans/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: int, session: Session = Depends(get_session)):
    """Get scan status, progress, and visibility score."""
    scan = session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(
        id=scan.id,
        project_id=scan.project_id,
        status=scan.status,
        providers_used=scan.providers_used,
        total_queries=scan.total_queries,
        completed_queries=scan.completed_queries,
        visibility_score=scan.visibility_score,
        error_message=scan.error_message,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
    )


@router.post(
    "/queries/{query_id}/scan",
    response_model=SingleQueryScanResponse,
)
async def scan_single_query(
    query_id: int,
    session: Session = Depends(get_session),
):
    """Scan a single query across all configured LLM providers.

    Returns results inline without creating a full Scan record.
    Useful for quick testing of individual queries.
    """
    query = session.get(Query, query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")

    project = session.get(Project, query.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from aiseo.services.visibility_scanner import run_single_query_scan

        result_dicts = await run_single_query_scan(project.id, query_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("single_query_scan_failed", query_id=query_id)
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}") from exc

    return SingleQueryScanResponse(
        query_id=query_id,
        query_text=query.text,
        results=[SingleQueryResultResponse(**r) for r in result_dicts],
    )


@router.get("/projects/{project_id}/history", response_model=list[ScanResponse])
def get_scan_history(project_id: int, session: Session = Depends(get_session)):
    """List all scans for a project, newest first."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    scans = session.exec(
        select(Scan)
        .where(Scan.project_id == project_id)
        .order_by(Scan.started_at.desc())
    ).all()

    return [
        ScanResponse(
            id=s.id,
            project_id=s.project_id,
            status=s.status,
            providers_used=s.providers_used,
            total_queries=s.total_queries,
            completed_queries=s.completed_queries,
            visibility_score=s.visibility_score,
            error_message=s.error_message,
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in scans
    ]
