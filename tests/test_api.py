"""Tests for the FastAPI API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aiseo.models.base import get_session
from aiseo.models.opportunity import Opportunity
from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Yield a session bound to the in-memory engine."""
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    """Create a TestClient with an overridden DB session."""
    from aiseo.main import create_app

    app = create_app()

    def _override_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


FAKE_BRAND_PROFILE = {
    "brand_name": "Acme",
    "brand_aliases": ["acme", "acme.com"],
    "description": "A project management tool for teams.",
    "category": "project management",
    "competitors": ["Trello", "Asana"],
    "features": ["task tracking", "team collaboration"],
    "target_audience": "SaaS founders",
}

FAKE_QUERIES = [
    {"text": "best project management tools", "intent_category": "discovery"},
    {"text": "acme vs trello", "intent_category": "comparison"},
    {"text": "how to track tasks", "intent_category": "problem"},
]


# ---------------------------------------------------------------------------
# Project routes
# ---------------------------------------------------------------------------


class TestCreateProject:
    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_create_project_success(self, mock_extract, mock_queries, client):
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = FAKE_QUERIES

        resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        assert resp.status_code == 201

        data = resp.json()
        assert data["brand_name"] == "Acme"
        assert data["url"] == "https://acme.com"
        assert data["category"] == "project management"
        assert set(data["brand_aliases"]) == {"acme", "acme.com"}
        assert data["competitors"] == ["Trello", "Asana"]
        assert len(data["queries"]) == 3

    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_create_project_extraction_failure(self, mock_extract, mock_queries, client):
        mock_extract.side_effect = RuntimeError("No API key")

        resp = client.post("/api/v1/projects", json={"url": "https://bad.com"})
        assert resp.status_code == 422
        assert "Brand extraction failed" in resp.json()["detail"]

    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_create_project_query_generation_failure_still_creates(
        self, mock_extract, mock_queries, client
    ):
        """Project should be created even if query generation fails."""
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.side_effect = RuntimeError("LLM error")

        resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["brand_name"] == "Acme"
        assert data["queries"] == []


class TestListProjects:
    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_list_projects(self, mock_extract, mock_queries, client):
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = []

        client.post("/api/v1/projects", json={"url": "https://acme.com"})
        client.post("/api/v1/projects", json={"url": "https://other.com"})

        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_projects_empty(self, client):
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetProject:
    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_get_project(self, mock_extract, mock_queries, client):
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = FAKE_QUERIES

        create_resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        project_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["brand_name"] == "Acme"
        assert len(data["queries"]) == 3

    def test_get_project_not_found(self, client):
        resp = client.get("/api/v1/projects/999")
        assert resp.status_code == 404


class TestUpdateProject:
    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_update_project_scalars(self, mock_extract, mock_queries, client):
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = []

        create_resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        project_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"brand_name": "Acme Pro", "category": "task management"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["brand_name"] == "Acme Pro"
        assert data["category"] == "task management"

    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_update_project_lists(self, mock_extract, mock_queries, client):
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = []

        create_resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        project_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"competitors": ["Monday", "ClickUp"], "features": ["gantt charts"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["competitors"] == ["Monday", "ClickUp"]
        assert data["features"] == ["gantt charts"]

    def test_update_project_not_found(self, client):
        resp = client.patch("/api/v1/projects/999", json={"brand_name": "X"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Query routes
# ---------------------------------------------------------------------------


class TestQueryManagement:
    def test_add_update_delete_query(self, client, engine):
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)
            project_id = project.id

        add_resp = client.post(
            f"/api/v1/projects/{project_id}/queries",
            json={"text": "best task software", "intent_category": "discovery"},
        )
        assert add_resp.status_code == 201
        query = add_resp.json()
        assert query["text"] == "best task software"

        patch_resp = client.patch(
            f"/api/v1/queries/{query['id']}",
            json={"text": "best task management software", "is_active": False},
        )
        assert patch_resp.status_code == 200
        updated = patch_resp.json()
        assert updated["text"] == "best task management software"
        assert updated["is_active"] is False

        delete_resp = client.delete(f"/api/v1/queries/{query['id']}")
        assert delete_resp.status_code == 204

    def test_add_query_with_search_volume(self, client, engine):
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)
            project_id = project.id

        resp = client.post(
            f"/api/v1/projects/{project_id}/queries",
            json={
                "text": "best ai seo tools",
                "intent_category": "discovery",
                "search_volume": 1200,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["search_volume"] == 1200
        assert data["volume_source"] == "csv"

    def test_add_query_project_not_found(self, client):
        resp = client.post(
            "/api/v1/projects/999/queries",
            json={"text": "best task software", "intent_category": "discovery"},
        )
        assert resp.status_code == 404

    def test_update_query_not_found(self, client):
        resp = client.patch(
            "/api/v1/queries/999",
            json={"is_active": False},
        )
        assert resp.status_code == 404

    def test_delete_query_not_found(self, client):
        resp = client.delete("/api/v1/queries/999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integrations routes
# ---------------------------------------------------------------------------


class TestIntegrationManagement:
    def test_test_integration_unknown_provider(self, client):
        resp = client.post("/api/v1/integrations/test", json={"provider": "unknown"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["configured"] is False

    @patch("aiseo.api.integrations._provider_from_name")
    def test_test_integration_success(self, mock_provider_factory, client):
        mock_provider = MagicMock()
        mock_provider.name = "chatgpt"
        mock_provider.is_configured.return_value = True
        mock_provider.query = AsyncMock(return_value=type(
            "_Resp",
            (),
            {"model": "gpt-4o-mini", "latency_ms": 111},
        )())
        mock_provider_factory.return_value = mock_provider

        resp = client.post("/api/v1/integrations/test", json={"provider": "chatgpt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "chatgpt"
        assert data["configured"] is True
        assert data["success"] is True
        assert data["model"] == "gpt-4o-mini"

    @patch("aiseo.api.integrations._provider_from_name")
    def test_test_integration_not_configured(self, mock_provider_factory, client):
        mock_provider = MagicMock()
        mock_provider.name = "chatgpt"
        mock_provider.is_configured.return_value = False
        mock_provider_factory.return_value = mock_provider

        resp = client.post("/api/v1/integrations/test", json={"provider": "chatgpt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["configured"] is False


# ---------------------------------------------------------------------------
# Scan routes
# ---------------------------------------------------------------------------


class TestTriggerScan:
    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_trigger_scan_creates_scan(self, mock_extract, mock_queries, client, engine):
        """Trigger a scan for a project with queries.

        We patch the Celery task import so it raises (no Redis), then
        patch run_scan to do nothing, letting us test the fallback path.
        """
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = FAKE_QUERIES

        create_resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        project_id = create_resp.json()["id"]

        with patch("aiseo.api.scans._redis_available", return_value=False), \
             patch("aiseo.services.visibility_scanner.run_scan", new_callable=AsyncMock) as mock_run, \
             patch("aiseo.services.scorer.compute_visibility_score") as mock_score, \
             patch("aiseo.services.opportunity_engine.compute_opportunities") as mock_opps:
            mock_run.return_value = None

            resp = client.post(f"/api/v1/projects/{project_id}/scan")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "completed"
        assert "scan_id" in data

    def test_trigger_scan_project_not_found(self, client):
        resp = client.post("/api/v1/projects/999/scan")
        assert resp.status_code == 404

    @patch("aiseo.services.query_generator.generate_all_queries", new_callable=AsyncMock)
    @patch("aiseo.services.brand_extractor.extract_brand_profile", new_callable=AsyncMock)
    def test_trigger_scan_no_queries(self, mock_extract, mock_queries, client):
        """Should 400 if project has no active queries."""
        mock_extract.return_value = FAKE_BRAND_PROFILE
        mock_queries.return_value = []  # no queries generated

        create_resp = client.post("/api/v1/projects", json={"url": "https://acme.com"})
        project_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/projects/{project_id}/scan")
        assert resp.status_code == 400
        assert "No active queries" in resp.json()["detail"]

    def test_trigger_scan_applies_demo_query_limit(self, client, engine):
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)

            for i in range(12):
                s.add(
                    Query(
                        project_id=project.id,
                        text=f"query {i}",
                        intent_category="discovery",
                        is_active=True,
                    )
                )
            s.commit()
            project_id = project.id

        with patch("aiseo.api.scans._redis_available", return_value=False), \
             patch("aiseo.services.visibility_scanner.run_scan", new_callable=AsyncMock) as mock_run, \
             patch("aiseo.services.scorer.compute_visibility_score"), \
             patch("aiseo.services.opportunity_engine.compute_opportunities"):
            mock_run.return_value = None
            resp = client.post(f"/api/v1/projects/{project_id}/scan")

        assert resp.status_code == 202
        scan_id = resp.json()["scan_id"]

        with Session(engine) as s:
            scan = s.get(Scan, scan_id)
            assert scan is not None
            assert scan.total_queries == 10


class TestGetScan:
    def test_get_scan(self, client, engine):
        # Seed a scan directly
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)

            scan = Scan(project_id=project.id, status="completed", visibility_score=72.5)
            s.add(scan)
            s.commit()
            s.refresh(scan)
            scan_id = scan.id

        resp = client.get(f"/api/v1/scans/{scan_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["visibility_score"] == 72.5

    def test_get_scan_not_found(self, client):
        resp = client.get("/api/v1/scans/999")
        assert resp.status_code == 404


class TestScanHistory:
    def test_scan_history(self, client, engine):
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)

            s.add(Scan(project_id=project.id, status="completed"))
            s.add(Scan(project_id=project.id, status="running"))
            s.commit()
            project_id = project.id

        resp = client.get(f"/api/v1/projects/{project_id}/history")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_scan_history_project_not_found(self, client):
        resp = client.get("/api/v1/projects/999/history")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Results routes
# ---------------------------------------------------------------------------


class TestGetResults:
    @pytest.fixture
    def seeded_results(self, engine):
        """Seed DB with project, queries, scan, and results."""
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)

            q1 = Query(
                project_id=project.id,
                text="best pm tools",
                intent_category="discovery",
            )
            q2 = Query(
                project_id=project.id,
                text="acme review",
                intent_category="comparison",
            )
            s.add_all([q1, q2])
            s.commit()
            s.refresh(q1)
            s.refresh(q2)

            scan = Scan(project_id=project.id, status="completed")
            s.add(scan)
            s.commit()
            s.refresh(scan)

            r1 = ScanResult(
                scan_id=scan.id,
                query_id=q1.id,
                provider="chatgpt",
                brand_mentioned=True,
                brand_position=1,
                competitors_mentioned_json=json.dumps(["Trello"]),
                citations_json=json.dumps(["https://acme.com"]),
                brands_ranked_json=json.dumps(
                    [
                        {"name": "Acme", "position": 1, "is_your_brand": True},
                        {"name": "Trello", "position": 2, "is_your_brand": False},
                    ]
                ),
            )
            r2 = ScanResult(
                scan_id=scan.id,
                query_id=q1.id,
                provider="perplexity",
                brand_mentioned=False,
                brands_ranked_json=json.dumps(
                    [
                        {"name": "Trello", "position": 1, "is_your_brand": False},
                        {"name": "Asana", "position": 2, "is_your_brand": False},
                    ]
                ),
            )
            r3 = ScanResult(
                scan_id=scan.id,
                query_id=q2.id,
                provider="chatgpt",
                brand_mentioned=True,
                brand_position=2,
                brands_ranked_json=json.dumps(
                    [
                        {"name": "Trello", "position": 1, "is_your_brand": False},
                        {"name": "Acme", "position": 2, "is_your_brand": True},
                    ]
                ),
            )
            s.add_all([r1, r2, r3])
            s.commit()
            scan_id = scan.id

        return scan_id

    def test_get_all_results(self, client, seeded_results):
        scan_id = seeded_results
        resp = client.get(f"/api/v1/scans/{scan_id}/results")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_filter_by_provider(self, client, seeded_results):
        scan_id = seeded_results
        resp = client.get(f"/api/v1/scans/{scan_id}/results?provider=chatgpt")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(r["provider"] == "chatgpt" for r in data)

    def test_filter_by_intent(self, client, seeded_results):
        scan_id = seeded_results
        resp = client.get(f"/api/v1/scans/{scan_id}/results?intent=comparison")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_results_scan_not_found(self, client):
        resp = client.get("/api/v1/scans/999/results")
        assert resp.status_code == 404

    def test_result_json_fields_deserialized(self, client, seeded_results):
        scan_id = seeded_results
        resp = client.get(f"/api/v1/scans/{scan_id}/results?provider=chatgpt")
        data = resp.json()
        # The first chatgpt result has competitors and citations
        chatgpt_mentioned = [r for r in data if r["brand_mentioned"]]
        assert len(chatgpt_mentioned) >= 1
        r = chatgpt_mentioned[0]
        assert isinstance(r["competitors_mentioned"], list)
        assert isinstance(r["citations"], list)
        assert isinstance(r["brands_ranked"], list)

    def test_get_rankings(self, client, seeded_results):
        scan_id = seeded_results
        resp = client.get(f"/api/v1/scans/{scan_id}/rankings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        first_query = data[0]
        assert "rankings" in first_query
        assert "per_provider" in first_query
        assert len(first_query["rankings"]) >= 1

    def test_get_rankings_scan_not_found(self, client):
        resp = client.get("/api/v1/scans/999/rankings")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Opportunities routes
# ---------------------------------------------------------------------------


class TestGetOpportunities:
    @pytest.fixture
    def seeded_opportunities(self, engine):
        """Seed DB with scan and opportunities."""
        with Session(engine) as s:
            project = Project(url="https://acme.com", brand_name="Acme")
            s.add(project)
            s.commit()
            s.refresh(project)

            q1 = Query(
                project_id=project.id,
                text="best pm tools",
                intent_category="discovery",
            )
            q2 = Query(
                project_id=project.id,
                text="acme vs trello",
                intent_category="comparison",
            )
            s.add_all([q1, q2])
            s.commit()
            s.refresh(q1)
            s.refresh(q2)

            scan = Scan(project_id=project.id, status="completed")
            s.add(scan)
            s.commit()
            s.refresh(scan)

            opp1 = Opportunity(
                scan_id=scan.id,
                query_id=q1.id,
                opportunity_type="invisible",
                impact_score=500.0,
                visibility_gap=0.8,
                recommendation="Create content for this query.",
            )
            opp1.competitors_visible = ["Trello", "Asana"]
            opp1.providers_missing = ["chatgpt", "perplexity"]

            opp2 = Opportunity(
                scan_id=scan.id,
                query_id=q2.id,
                opportunity_type="competitor_dominated",
                impact_score=200.0,
                visibility_gap=0.4,
                recommendation="Strengthen comparison content.",
            )
            opp2.competitors_visible = ["Trello"]
            opp2.providers_missing = []

            s.add_all([opp1, opp2])
            s.commit()
            scan_id = scan.id

        return scan_id

    def test_get_all_opportunities(self, client, seeded_opportunities):
        scan_id = seeded_opportunities
        resp = client.get(f"/api/v1/scans/{scan_id}/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Sorted by impact_score desc
        assert data[0]["impact_score"] >= data[1]["impact_score"]

    def test_filter_by_type(self, client, seeded_opportunities):
        scan_id = seeded_opportunities
        resp = client.get(f"/api/v1/scans/{scan_id}/opportunities?type=invisible")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["opportunity_type"] == "invisible"

    def test_limit(self, client, seeded_opportunities):
        scan_id = seeded_opportunities
        resp = client.get(f"/api/v1/scans/{scan_id}/opportunities?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_opportunities_scan_not_found(self, client):
        resp = client.get("/api/v1/scans/999/opportunities")
        assert resp.status_code == 404

    def test_opportunity_json_fields_deserialized(self, client, seeded_opportunities):
        scan_id = seeded_opportunities
        resp = client.get(f"/api/v1/scans/{scan_id}/opportunities")
        data = resp.json()
        opp = data[0]
        assert isinstance(opp["competitors_visible"], list)
        assert isinstance(opp["providers_missing"], list)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
