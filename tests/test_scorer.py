"""Tests for the AI Visibility Score service."""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan
from aiseo.services.scorer import (
    VisibilityScore,
    compute_visibility_score,
    score_single_result,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def seeded_db(engine):
    """Seed the DB with a project, queries, scan, and results.

    Returns (engine, scan_id) for use in tests.
    """
    with Session(engine) as session:
        project = Project(id=1, url="https://acme.com", brand_name="Acme")
        session.add(project)
        session.flush()

        q1 = Query(
            id=1,
            project_id=1,
            text="best project management tools",
            intent_category="discovery",
            search_volume=1000,
        )
        q2 = Query(
            id=2,
            project_id=1,
            text="acme vs competitor",
            intent_category="comparison",
            search_volume=500,
        )
        q3 = Query(
            id=3,
            project_id=1,
            text="how to manage projects",
            intent_category="problem",
            search_volume=None,  # will default to 1
        )
        session.add_all([q1, q2, q3])
        session.flush()

        scan = Scan(id=1, project_id=1, status="running")
        session.add(scan)
        session.flush()

        results = [
            # q1 chatgpt: mentioned, position 1, positive, cited
            ScanResult(
                scan_id=1,
                query_id=1,
                provider="chatgpt",
                brand_mentioned=True,
                brand_position=1,
                brand_sentiment="positive",
                brand_cited=True,
                competitors_mentioned_json=json.dumps(["Rival"]),
            ),
            # q1 perplexity: mentioned, position 3, neutral, not cited
            ScanResult(
                scan_id=1,
                query_id=1,
                provider="perplexity",
                brand_mentioned=True,
                brand_position=3,
                brand_sentiment="neutral",
                brand_cited=False,
                competitors_mentioned_json=json.dumps(["Rival", "OtherCo"]),
            ),
            # q2 chatgpt: not mentioned
            ScanResult(
                scan_id=1,
                query_id=2,
                provider="chatgpt",
                brand_mentioned=False,
                competitors_mentioned_json=json.dumps(["Rival"]),
            ),
            # q2 perplexity: mentioned, position 2, negative
            ScanResult(
                scan_id=1,
                query_id=2,
                provider="perplexity",
                brand_mentioned=True,
                brand_position=2,
                brand_sentiment="negative",
                brand_cited=False,
                competitors_mentioned_json=json.dumps([]),
            ),
            # q3 chatgpt: mentioned, position 4, neutral
            ScanResult(
                scan_id=1,
                query_id=3,
                provider="chatgpt",
                brand_mentioned=True,
                brand_position=4,
                brand_sentiment="neutral",
                brand_cited=False,
                competitors_mentioned_json=json.dumps(["OtherCo"]),
            ),
        ]
        session.add_all(results)
        session.commit()

    return engine, 1


# --- score_single_result unit tests ---


class TestScoreSingleResult:
    def _make_result(self, **kwargs) -> ScanResult:
        defaults = dict(
            scan_id=1,
            query_id=1,
            provider="chatgpt",
            brand_mentioned=False,
            brand_position=None,
            brand_sentiment=None,
            brand_cited=False,
        )
        defaults.update(kwargs)
        return ScanResult(**defaults)

    def test_not_mentioned_scores_zero(self):
        r = self._make_result(brand_mentioned=False)
        assert score_single_result(r) == 0.0

    def test_mentioned_position_1_positive_cited(self):
        r = self._make_result(
            brand_mentioned=True,
            brand_position=1,
            brand_sentiment="positive",
            brand_cited=True,
        )
        # (1.0 + 0.2) * 1.0 = 1.2
        assert score_single_result(r) == pytest.approx(1.2)

    def test_mentioned_position_2_neutral_not_cited(self):
        r = self._make_result(
            brand_mentioned=True,
            brand_position=2,
            brand_sentiment="neutral",
            brand_cited=False,
        )
        # (0.7 + 0.0) * 0.7 = 0.49
        assert score_single_result(r) == pytest.approx(0.49)

    def test_mentioned_position_3_negative(self):
        r = self._make_result(
            brand_mentioned=True,
            brand_position=3,
            brand_sentiment="negative",
            brand_cited=False,
        )
        # (0.5 + 0.0) * 0.3 = 0.15
        assert score_single_result(r) == pytest.approx(0.15)

    def test_mentioned_position_5_defaults_to_03(self):
        r = self._make_result(
            brand_mentioned=True,
            brand_position=5,
            brand_sentiment="positive",
        )
        # (0.3 + 0.0) * 1.0 = 0.3
        assert score_single_result(r) == pytest.approx(0.3)

    def test_mentioned_no_position_scores_zero(self):
        r = self._make_result(
            brand_mentioned=True,
            brand_position=None,
            brand_sentiment="positive",
        )
        # (0.0 + 0.0) * 1.0 = 0.0
        assert score_single_result(r) == 0.0

    def test_none_sentiment_treated_as_neutral(self):
        r = self._make_result(
            brand_mentioned=True,
            brand_position=1,
            brand_sentiment=None,
        )
        # (1.0 + 0.0) * 0.7 = 0.7
        assert score_single_result(r) == pytest.approx(0.7)


# --- compute_visibility_score integration tests ---


class TestComputeVisibilityScore:
    def test_returns_visibility_score_dataclass(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        assert isinstance(result, VisibilityScore)

    def test_overall_score_in_range(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        assert 0.0 <= result.overall <= 100.0

    def test_per_llm_keys(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        assert set(result.per_llm.keys()) == {"chatgpt", "perplexity"}

    def test_per_category_keys(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        assert set(result.per_category.keys()) == {
            "discovery",
            "comparison",
            "problem",
        }

    def test_competitor_scores_present(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        assert "Rival" in result.competitor_scores
        assert "OtherCo" in result.competitor_scores

    def test_competitor_scores_are_percentages(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        for score in result.competitor_scores.values():
            assert 0.0 <= score <= 100.0

    def test_updates_scan_visibility_score(self, seeded_db):
        engine, scan_id = seeded_db
        result = compute_visibility_score(scan_id, engine=engine)
        with Session(engine) as session:
            scan = session.get(Scan, scan_id)
            assert scan.visibility_score == result.overall

    def test_empty_scan_returns_zero(self, engine):
        """A scan with no results should return all zeros."""
        with Session(engine) as session:
            project = Project(id=1, url="https://x.com", brand_name="X")
            session.add(project)
            session.flush()
            scan = Scan(id=99, project_id=1, status="completed")
            session.add(scan)
            session.commit()

        result = compute_visibility_score(99, engine=engine)
        assert result.overall == 0.0
        assert result.per_llm == {}
        assert result.per_category == {}
        assert result.competitor_scores == {}

    def test_search_volume_weighting(self, engine):
        """Higher search volume queries should have more weight."""
        with Session(engine) as session:
            project = Project(id=1, url="https://x.com", brand_name="X")
            session.add(project)
            session.flush()

            # High-volume query: brand mentioned at position 1, positive
            q_high = Query(
                id=1,
                project_id=1,
                text="high volume",
                intent_category="discovery",
                search_volume=10000,
            )
            # Low-volume query: brand not mentioned
            q_low = Query(
                id=2,
                project_id=1,
                text="low volume",
                intent_category="discovery",
                search_volume=1,
            )
            session.add_all([q_high, q_low])
            session.flush()

            scan = Scan(id=1, project_id=1, status="running")
            session.add(scan)
            session.flush()

            r1 = ScanResult(
                scan_id=1,
                query_id=1,
                provider="chatgpt",
                brand_mentioned=True,
                brand_position=1,
                brand_sentiment="positive",
                brand_cited=True,
            )
            r2 = ScanResult(
                scan_id=1,
                query_id=2,
                provider="chatgpt",
                brand_mentioned=False,
            )
            session.add_all([r1, r2])
            session.commit()

        result = compute_visibility_score(1, engine=engine)
        # Score should be close to 100 because the high-volume query dominates
        assert result.overall > 90.0

    def test_all_mentioned_perfect_score(self, engine):
        """All queries mentioned at position 1, positive, cited = 100."""
        with Session(engine) as session:
            project = Project(id=1, url="https://x.com", brand_name="X")
            session.add(project)
            session.flush()

            q = Query(
                id=1,
                project_id=1,
                text="test",
                intent_category="discovery",
                search_volume=100,
            )
            session.add(q)
            session.flush()

            scan = Scan(id=1, project_id=1, status="running")
            session.add(scan)
            session.flush()

            r = ScanResult(
                scan_id=1,
                query_id=1,
                provider="chatgpt",
                brand_mentioned=True,
                brand_position=1,
                brand_sentiment="positive",
                brand_cited=True,
            )
            session.add(r)
            session.commit()

        result = compute_visibility_score(1, engine=engine)
        assert result.overall == 100.0

    def test_none_mentioned_zero_score(self, engine):
        """No mentions at all = 0."""
        with Session(engine) as session:
            project = Project(id=1, url="https://x.com", brand_name="X")
            session.add(project)
            session.flush()

            q = Query(
                id=1,
                project_id=1,
                text="test",
                intent_category="discovery",
            )
            session.add(q)
            session.flush()

            scan = Scan(id=1, project_id=1, status="running")
            session.add(scan)
            session.flush()

            r = ScanResult(
                scan_id=1,
                query_id=1,
                provider="chatgpt",
                brand_mentioned=False,
            )
            session.add(r)
            session.commit()

        result = compute_visibility_score(1, engine=engine)
        assert result.overall == 0.0
