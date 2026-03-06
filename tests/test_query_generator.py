"""Tests for query generation service."""

from unittest.mock import AsyncMock, patch

import pytest

from aiseo.services.query_generator import generate_all_queries, generate_template_queries

SAMPLE_PROFILE = {
    "brand_name": "PostZaper",
    "brand_aliases": ["postzaper", "postzaper.com"],
    "description": "Social media scheduling and automation tool",
    "category": "social media automation",
    "competitors": ["Buffer", "Hootsuite", "Later"],
    "features": [
        "schedule social media posts",
        "auto-publish content",
        "analytics dashboard",
    ],
    "target_audience": "SaaS founders and marketers",
}


class TestGenerateTemplateQueries:
    def test_generates_discovery_queries(self):
        queries = generate_template_queries(SAMPLE_PROFILE)
        texts = [q["text"] for q in queries]
        assert any("social media automation" in t for t in texts)

    def test_generates_comparison_queries(self):
        queries = generate_template_queries(SAMPLE_PROFILE)
        texts = [q["text"] for q in queries]
        assert any("PostZaper vs Buffer" in t for t in texts)
        assert any("PostZaper alternatives" in t for t in texts)

    def test_generates_problem_queries(self):
        queries = generate_template_queries(SAMPLE_PROFILE)
        texts = [q["text"] for q in queries]
        assert any("schedule social media posts" in t for t in texts)

    def test_generates_recommendation_queries(self):
        queries = generate_template_queries(SAMPLE_PROFILE)
        intents = {q["intent_category"] for q in queries}
        assert "recommendation" in intents

    def test_no_duplicate_queries(self):
        queries = generate_template_queries(SAMPLE_PROFILE)
        texts = [q["text"].lower() for q in queries]
        assert len(texts) == len(set(texts))

    def test_all_queries_have_intent(self):
        queries = generate_template_queries(SAMPLE_PROFILE)
        valid_intents = {"discovery", "comparison", "problem", "recommendation"}
        for q in queries:
            assert q["intent_category"] in valid_intents


class TestGenerateAllQueries:
    @pytest.mark.asyncio
    async def test_respects_max_queries(self):
        with patch(
            "aiseo.services.query_generator.generate_llm_queries",
            new_callable=AsyncMock,
            return_value=[],
        ):
            queries = await generate_all_queries(SAMPLE_PROFILE, max_queries=5)
            assert len(queries) <= 5

    @pytest.mark.asyncio
    async def test_deduplicates_llm_queries(self):
        llm_queries = [
            {"text": "best social media automation tools", "intent_category": "discovery"},
            {"text": "unique query from llm", "intent_category": "discovery"},
        ]
        with patch(
            "aiseo.services.query_generator.generate_llm_queries",
            new_callable=AsyncMock,
            return_value=llm_queries,
        ):
            queries = await generate_all_queries(SAMPLE_PROFILE, max_queries=100)
            texts = [q["text"].lower() for q in queries]
            assert len(texts) == len(set(texts))
