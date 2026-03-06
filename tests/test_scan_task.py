"""Tests for the Celery scan task with mocked service calls."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from aiseo.models.scan import Scan


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    """In-memory SQLite engine with Scan table created."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def scan_row(engine):
    """Insert a pending Scan row and return its id."""
    scan = Scan(
        project_id=1,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )
    with Session(engine) as session:
        session.add(scan)
        session.commit()
        session.refresh(scan)
        return scan.id


@pytest.fixture(autouse=True)
def _patch_engine(engine):
    """Make get_engine() return our in-memory engine everywhere."""
    with patch("aiseo.tasks.scan_task.get_engine", return_value=engine), \
         patch("aiseo.services.visibility_scanner.get_engine", return_value=engine):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunScanTask:
    def test_successful_scan(self, engine, scan_row):
        """Happy path: run_scan completes, scorer and opportunity engine are called."""
        mock_scorer = MagicMock()
        mock_opportunities = MagicMock()

        with patch("aiseo.tasks.scan_task.asyncio.run") as mock_asyncio_run, \
             patch(
                 "aiseo.services.scorer.compute_visibility_score",
                 mock_scorer,
                 create=True,
             ), \
             patch(
                 "aiseo.services.opportunity_engine.compute_opportunities",
                 mock_opportunities,
                 create=True,
             ):
            from aiseo.tasks.scan_task import run_scan_task

            result = run_scan_task(project_id=1, scan_id=scan_row)

        assert result["status"] == "completed"
        assert result["scan_id"] == scan_row

        # asyncio.run was called with the run_scan coroutine
        mock_asyncio_run.assert_called_once()

        # Scorer and opportunity engine were invoked
        mock_scorer.assert_called_once_with(scan_row)
        mock_opportunities.assert_called_once_with(scan_row, 1)

        # DB row updated
        with Session(engine) as session:
            scan = session.get(Scan, scan_row)
            assert scan.status == "completed"
            assert scan.completed_at is not None

    def test_scan_failure_updates_db(self, engine, scan_row):
        """When run_scan raises, the Scan row is marked failed."""
        with patch(
            "aiseo.tasks.scan_task.asyncio.run",
            side_effect=RuntimeError("provider exploded"),
        ):
            from aiseo.tasks.scan_task import run_scan_task

            result = run_scan_task(project_id=1, scan_id=scan_row)

        assert result["status"] == "failed"
        assert "provider exploded" in result["error"]

        with Session(engine) as session:
            scan = session.get(Scan, scan_row)
            assert scan.status == "failed"
            assert "provider exploded" in scan.error_message

    def test_scorer_failure_does_not_crash_task(self, engine, scan_row):
        """If the scorer raises, the task still completes."""
        with patch("aiseo.tasks.scan_task.asyncio.run"), \
             patch(
                 "aiseo.services.scorer.compute_visibility_score",
                 side_effect=ImportError("scorer not built yet"),
                 create=True,
             ), \
             patch(
                 "aiseo.services.opportunity_engine.compute_opportunities",
                 MagicMock(),
                 create=True,
             ):
            from aiseo.tasks.scan_task import run_scan_task

            result = run_scan_task(project_id=1, scan_id=scan_row)

        assert result["status"] == "completed"

    def test_opportunity_engine_failure_does_not_crash_task(self, engine, scan_row):
        """If the opportunity engine raises, the task still completes."""
        with patch("aiseo.tasks.scan_task.asyncio.run"), \
             patch(
                 "aiseo.services.scorer.compute_visibility_score",
                 MagicMock(),
                 create=True,
             ), \
             patch(
                 "aiseo.services.opportunity_engine.compute_opportunities",
                 side_effect=ImportError("engine not built yet"),
                 create=True,
             ):
            from aiseo.tasks.scan_task import run_scan_task

            result = run_scan_task(project_id=1, scan_id=scan_row)

        assert result["status"] == "completed"

    def test_scan_already_failed_not_overwritten(self, engine, scan_row):
        """If run_scan marked the scan as failed, the task preserves that status."""
        def fake_run_scan(coro):
            """Simulate run_scan marking the scan as failed internally."""
            with Session(engine) as session:
                scan = session.get(Scan, scan_row)
                scan.status = "failed"
                scan.error_message = "No providers configured"
                session.add(scan)
                session.commit()

        with patch("aiseo.tasks.scan_task.asyncio.run", side_effect=fake_run_scan), \
             patch(
                 "aiseo.services.scorer.compute_visibility_score",
                 MagicMock(),
                 create=True,
             ), \
             patch(
                 "aiseo.services.opportunity_engine.compute_opportunities",
                 MagicMock(),
                 create=True,
             ):
            from aiseo.tasks.scan_task import run_scan_task

            result = run_scan_task(project_id=1, scan_id=scan_row)

        # Task returns completed but DB stays failed
        with Session(engine) as session:
            scan = session.get(Scan, scan_row)
            assert scan.status == "failed"
            assert scan.error_message == "No providers configured"
