"""Tests for the opportunity engine."""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

from aiseo.models.opportunity import Opportunity
from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan
from aiseo.services.opportunity_engine import compute_opportunities


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


def _seed_project(session: Session) -> Project:
    project = Project(id=1, url="https://acme.com", brand_name="Acme")
    project.competitors = ["Rival", "OtherCo"]
    session.add(project)
    session.flush()
    return project


def _seed_scan(session: Session) -> Scan:
    scan = Scan(id=1, project_id=1, status="completed")
    session.add(scan)
    session.flush()
    return scan


class TestComputeOpportunities:
    def test_invisible_opportunity(self, engine):
        """Brand not mentioned on any provider but competitors are."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="best pm tools", intent_category="discovery", search_volume=1000)
            session.add(q)
            _seed_scan(session)

            r = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=False,
                competitors_mentioned_json=json.dumps(["Rival"]),
            )
            session.add(r)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 1
        assert opps[0].opportunity_type == "invisible"
        assert opps[0].impact_score > 0
        assert "invisible" in opps[0].recommendation.lower()

    def test_partial_visibility(self, engine):
        """Brand mentioned on some providers but not others."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="acme review", intent_category="comparison", search_volume=500)
            session.add(q)
            _seed_scan(session)

            r1 = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=True, brand_position=1, brand_sentiment="positive",
            )
            r2 = ScanResult(
                scan_id=1, query_id=1, provider="perplexity",
                brand_mentioned=False,
                competitors_mentioned_json=json.dumps(["Rival"]),
            )
            session.add_all([r1, r2])
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 1
        assert opps[0].opportunity_type == "partial_visibility"
        assert "perplexity" in opps[0].providers_missing

    def test_competitor_dominated(self, engine):
        """Brand mentioned but at lower position than competitors."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="best tools", intent_category="discovery", search_volume=800)
            session.add(q)
            _seed_scan(session)

            r = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=True, brand_position=3, brand_sentiment="neutral",
                competitors_mentioned_json=json.dumps(["Rival"]),
            )
            session.add(r)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 1
        assert opps[0].opportunity_type == "competitor_dominated"

    def test_negative_sentiment(self, engine):
        """Brand mentioned but with negative sentiment."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="acme problems", intent_category="problem", search_volume=200)
            session.add(q)
            _seed_scan(session)

            r = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=True, brand_position=1, brand_sentiment="negative",
            )
            session.add(r)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 1
        assert opps[0].opportunity_type == "negative_sentiment"

    def test_no_opportunity_when_well_positioned(self, engine):
        """Brand mentioned at position 1 with no competitors = no opportunity."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="acme features", intent_category="discovery", search_volume=100)
            session.add(q)
            _seed_scan(session)

            r = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=True, brand_position=1, brand_sentiment="positive",
            )
            session.add(r)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 0

    def test_sorted_by_impact_score(self, engine):
        """Opportunities are returned sorted by impact_score descending."""
        with Session(engine) as session:
            _seed_project(session)
            q1 = Query(id=1, project_id=1, text="low volume", intent_category="discovery", search_volume=10)
            q2 = Query(id=2, project_id=1, text="high volume", intent_category="discovery", search_volume=5000)
            session.add_all([q1, q2])
            _seed_scan(session)

            # Both invisible with competitors
            for qid in [1, 2]:
                r = ScanResult(
                    scan_id=1, query_id=qid, provider="chatgpt",
                    brand_mentioned=False,
                    competitors_mentioned_json=json.dumps(["Rival"]),
                )
                session.add(r)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 2
        assert opps[0].impact_score >= opps[1].impact_score

    def test_opportunities_persisted_to_db(self, engine):
        """Opportunities are saved to the database."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="test", intent_category="discovery", search_volume=100)
            session.add(q)
            _seed_scan(session)
            r = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=False,
                competitors_mentioned_json=json.dumps(["Rival"]),
            )
            session.add(r)
            session.commit()

        compute_opportunities(1, 1, engine=engine)

        with Session(engine) as session:
            opps = session.exec(
                __import__("sqlmodel").select(Opportunity).where(Opportunity.scan_id == 1)
            ).all()
            assert len(opps) == 1
            assert opps[0].id is not None

    def test_empty_scan_returns_empty(self, engine):
        """No results for scan returns empty list."""
        with Session(engine) as session:
            _seed_project(session)
            _seed_scan(session)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert opps == []

    def test_missing_project_returns_empty(self, engine):
        opps = compute_opportunities(1, 999, engine=engine)
        assert opps == []

    def test_default_volume_when_none(self, engine):
        """search_volume=None uses 1 as default weight."""
        with Session(engine) as session:
            _seed_project(session)
            q = Query(id=1, project_id=1, text="niche query", intent_category="discovery", search_volume=None)
            session.add(q)
            _seed_scan(session)
            r = ScanResult(
                scan_id=1, query_id=1, provider="chatgpt",
                brand_mentioned=False,
                competitors_mentioned_json=json.dumps(["Rival"]),
            )
            session.add(r)
            session.commit()

        opps = compute_opportunities(1, 1, engine=engine)
        assert len(opps) == 1
        assert opps[0].impact_score > 0
