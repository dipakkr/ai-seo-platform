"""Tests for search volume adapters."""

import csv
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from aiseo.volume.autocomplete import AutocompleteAdapter
from aiseo.volume.csv_upload import CSVAdapter
from aiseo.volume.google_ads import GoogleAdsAdapter


# ---------------------------------------------------------------------------
# AutocompleteAdapter
# ---------------------------------------------------------------------------

class TestAutocompleteAdapter:
    @pytest.mark.asyncio
    async def test_returns_volumes_for_keywords(self):
        adapter = AutocompleteAdapter(max_concurrent=2)

        def mock_response(keyword: str) -> httpx.Response:
            suggestions = {
                "best pm tools": ["s1", "s2", "s3", "s4", "s5"],
                "niche query": ["s1"],
            }
            data = [keyword, suggestions.get(keyword, [])]
            request = httpx.Request("GET", "https://suggestqueries.google.com/complete/search")
            return httpx.Response(200, json=data, request=request)

        async def mock_get(url, params=None, **kwargs):
            keyword = params["q"]
            return mock_response(keyword)

        with patch("aiseo.volume.autocomplete.httpx.AsyncClient") as mock_client_cls:
            client_instance = AsyncMock()
            client_instance.get = mock_get
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = client_instance

            result = await adapter.get_volumes(["best pm tools", "niche query"])

        assert result["best pm tools"] == 500   # 5 suggestions
        assert result["niche query"] == 10       # 1 suggestion

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        adapter = AutocompleteAdapter(max_concurrent=1)

        async def mock_get(url, params=None, **kwargs):
            raise httpx.ConnectError("network down")

        with patch("aiseo.volume.autocomplete.httpx.AsyncClient") as mock_client_cls:
            client_instance = AsyncMock()
            client_instance.get = mock_get
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = client_instance

            result = await adapter.get_volumes(["failing query"])

        assert result["failing query"] is None


# ---------------------------------------------------------------------------
# CSVAdapter
# ---------------------------------------------------------------------------

class TestCSVAdapter:
    def _write_csv(self, path: Path, rows: list[dict]):
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["keyword", "volume"])
            writer.writeheader()
            writer.writerows(rows)

    @pytest.mark.asyncio
    async def test_exact_match(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        self._write_csv(csv_file, [
            {"keyword": "best pm tools", "volume": "5000"},
            {"keyword": "project management", "volume": "12000"},
        ])

        adapter = CSVAdapter(csv_file)
        result = await adapter.get_volumes(["best pm tools", "unknown query"])

        assert result["best pm tools"] == 5000
        assert result["unknown query"] is None

    @pytest.mark.asyncio
    async def test_fuzzy_match(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        self._write_csv(csv_file, [
            {"keyword": "best project management tools", "volume": "8000"},
        ])

        adapter = CSVAdapter(csv_file)
        # Slight variation should still match at threshold 85
        result = await adapter.get_volumes(["best project management tool"])

        assert result["best project management tool"] == 8000

    @pytest.mark.asyncio
    async def test_missing_file(self, tmp_path):
        adapter = CSVAdapter(tmp_path / "nonexistent.csv")
        result = await adapter.get_volumes(["anything"])
        assert result["anything"] is None

    @pytest.mark.asyncio
    async def test_empty_csv(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        self._write_csv(csv_file, [])

        adapter = CSVAdapter(csv_file)
        result = await adapter.get_volumes(["test"])
        assert result["test"] is None


# ---------------------------------------------------------------------------
# GoogleAdsAdapter
# ---------------------------------------------------------------------------

class TestGoogleAdsAdapter:
    def test_is_configured_false_by_default(self):
        with patch("aiseo.volume.google_ads.get_settings") as mock:
            mock.return_value.google_ads_developer_token = None
            mock.return_value.google_ads_client_id = None
            adapter = GoogleAdsAdapter()
            assert adapter.is_configured() is False

    def test_is_configured_true_with_credentials(self):
        with patch("aiseo.volume.google_ads.get_settings") as mock:
            mock.return_value.google_ads_developer_token = "token123"
            mock.return_value.google_ads_client_id = "client123"
            adapter = GoogleAdsAdapter()
            assert adapter.is_configured() is True

    @pytest.mark.asyncio
    async def test_unconfigured_returns_none(self):
        with patch("aiseo.volume.google_ads.get_settings") as mock:
            mock.return_value.google_ads_developer_token = None
            mock.return_value.google_ads_client_id = None
            adapter = GoogleAdsAdapter()
            result = await adapter.get_volumes(["test keyword"])
            assert result["test keyword"] is None
