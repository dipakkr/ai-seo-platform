"""Tests for brand extraction service."""

from unittest.mock import AsyncMock, patch

import pytest

from aiseo.services.brand_extractor import extract_brand_profile
from aiseo.utils.scraper import build_extraction_text, extract_metadata


class TestExtractMetadata:
    def test_extracts_title(self):
        html = "<html><head><title>PostZaper - Social Media Automation</title></head><body></body></html>"
        meta = extract_metadata(html)
        assert meta["title"] == "PostZaper - Social Media Automation"

    def test_extracts_meta_description(self):
        html = '<html><head><meta name="description" content="Automate your posts"></head><body></body></html>'
        meta = extract_metadata(html)
        assert meta["meta_description"] == "Automate your posts"

    def test_extracts_og_tags(self):
        html = """<html><head>
            <meta property="og:title" content="OG Title">
            <meta property="og:description" content="OG Desc">
            <meta property="og:site_name" content="MySite">
        </head><body></body></html>"""
        meta = extract_metadata(html)
        assert meta["og_title"] == "OG Title"
        assert meta["og_description"] == "OG Desc"
        assert meta["og_site_name"] == "MySite"

    def test_extracts_headings(self):
        html = "<html><body><h1>Main Title</h1><h2>Feature 1</h2><h2>Feature 2</h2></body></html>"
        meta = extract_metadata(html)
        assert meta["h1"] == "Main Title"
        assert meta["h2s"] == ["Feature 1", "Feature 2"]

    def test_finds_about_link(self):
        html = '<html><body><a href="/about">About Us</a></body></html>'
        meta = extract_metadata(html)
        assert meta["about_link"] == "/about"

    def test_strips_scripts_and_styles(self):
        html = "<html><body><script>alert('x')</script><style>.x{}</style><p>Content</p></body></html>"
        meta = extract_metadata(html)
        assert "alert" not in meta["body_text"]
        assert "Content" in meta["body_text"]

    def test_truncates_body_text(self):
        html = "<html><body><p>" + "word " * 2000 + "</p></body></html>"
        meta = extract_metadata(html)
        assert len(meta["body_text"]) <= 5000


class TestBuildExtractionText:
    def test_builds_text_from_metadata(self):
        meta = {
            "title": "My App",
            "og_site_name": "MyApp",
            "meta_description": "A great app",
            "og_description": "A different desc",
            "h1": "Welcome",
            "h2s": ["Features", "Pricing"],
            "body_text": "Some content here.",
            "about_link": None,
        }
        text = build_extraction_text(meta)
        assert "My App" in text
        assert "A great app" in text
        assert "Features, Pricing" in text


class TestExtractBrandProfile:
    @pytest.mark.asyncio
    async def test_extract_brand_profile_with_openai(self):
        mock_html = """<html><head>
            <title>TestBrand - Project Management</title>
            <meta name="description" content="Best project management tool">
        </head><body><h1>TestBrand</h1><p>Manage projects easily.</p></body></html>"""

        mock_llm_response = '{"brand_name": "TestBrand", "brand_aliases": ["testbrand"], "description": "A project management tool", "category": "project management", "competitors": ["Asana", "Trello"], "features": ["task tracking", "team collaboration"], "target_audience": "small teams"}'

        with (
            patch("aiseo.services.brand_extractor.fetch_page", new_callable=AsyncMock) as mock_fetch,
            patch("aiseo.services.brand_extractor._call_llm_for_extraction", new_callable=AsyncMock) as mock_llm,
        ):
            mock_fetch.return_value = mock_html
            mock_llm.return_value = mock_llm_response

            result = await extract_brand_profile("https://testbrand.com")

            assert result["brand_name"] == "TestBrand"
            assert result["category"] == "project management"
            assert "Asana" in result["competitors"]
            assert "testbrand.com" in result["brand_aliases"]
