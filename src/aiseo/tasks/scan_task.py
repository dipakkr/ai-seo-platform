"""Celery task that wraps the async visibility scanner."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlmodel import Session

from aiseo.models.base import get_engine
from aiseo.models.scan import Scan
from aiseo.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="aiseo.scan", bind=True, max_retries=0)
def run_scan_task(self, project_id: int, scan_id: int) -> dict:
    """Run a full visibility scan, then score results and find opportunities.

    This is a synchronous Celery task that drives the async ``run_scan``
    coroutine via ``asyncio.run()``.  After scanning completes it invokes
    the scorer and opportunity engine (lazy-imported because they may be
    built in parallel by other contributors).

    Args:
        project_id: ID of the project to scan.
        scan_id: ID of the Scan record tracking this run.

    Returns:
        A small summary dict with ``scan_id`` and ``status``.
    """
    engine = get_engine()

    try:
        # --- Mark scan as running (belt-and-suspenders; scanner also sets it) ---
        _update_scan_status(engine, scan_id, "running")

        # --- Execute the async scan ---
        from aiseo.services.visibility_scanner import run_scan

        asyncio.run(run_scan(project_id, scan_id))

        # --- Post-scan: scoring ---
        try:
            from aiseo.services.scorer import compute_visibility_score

            compute_visibility_score(scan_id)
        except Exception:
            logger.exception("Scorer failed for scan %s", scan_id)

        # --- Post-scan: opportunity detection ---
        try:
            from aiseo.services.opportunity_engine import compute_opportunities

            compute_opportunities(scan_id, project_id)
        except Exception:
            logger.exception("Opportunity engine failed for scan %s", scan_id)

        # --- Final status (only if scanner didn't already fail) ---
        with Session(engine) as session:
            scan = session.get(Scan, scan_id)
            if scan is not None and scan.status != "failed":
                scan.status = "completed"
                scan.completed_at = datetime.now(timezone.utc)
                session.add(scan)
                session.commit()

        logger.info("Scan task finished: scan_id=%s project_id=%s", scan_id, project_id)
        return {"scan_id": scan_id, "status": "completed"}

    except Exception as exc:
        logger.exception("Scan task failed: scan_id=%s", scan_id)
        _fail_scan(engine, scan_id, str(exc))
        return {"scan_id": scan_id, "status": "failed", "error": str(exc)}


def _update_scan_status(engine, scan_id: int, status: str) -> None:
    """Set the scan status."""
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is not None:
            scan.status = status
            session.add(scan)
            session.commit()


def _fail_scan(engine, scan_id: int, message: str) -> None:
    """Mark a scan as failed with an error message."""
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is not None:
            scan.status = "failed"
            scan.error_message = message
            scan.completed_at = datetime.now(timezone.utc)
            session.add(scan)
            session.commit()
