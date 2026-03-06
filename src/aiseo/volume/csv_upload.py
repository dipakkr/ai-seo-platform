"""CSV-based search volume adapter with fuzzy keyword matching."""

import csv
import logging
from pathlib import Path

from rapidfuzz import fuzz, process

from aiseo.volume.base import SearchVolumeAdapter

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 85


class CSVAdapter(SearchVolumeAdapter):
    """Load search volumes from a user-provided CSV file.

    The CSV must have columns ``keyword`` and ``volume``.
    Keywords are matched to input queries using fuzzy matching (threshold 85).
    """

    name = "csv"

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)
        self._data: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        """Parse the CSV file into an in-memory lookup dict."""
        if not self._file_path.exists():
            logger.warning("CSV file not found: %s", self._file_path)
            return

        with open(self._file_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                keyword = row.get("keyword", "").strip()
                volume_str = row.get("volume", "").strip()
                if keyword and volume_str:
                    try:
                        self._data[keyword.lower()] = int(volume_str)
                    except ValueError:
                        logger.warning("Skipping invalid volume %r for keyword %r", volume_str, keyword)

    async def get_volumes(self, keywords: list[str]) -> dict[str, int | None]:
        """Match each input keyword to CSV data using fuzzy matching."""
        if not self._data:
            return {kw: None for kw in keywords}

        csv_keywords = list(self._data.keys())
        results: dict[str, int | None] = {}

        for kw in keywords:
            match = process.extractOne(
                kw.lower(),
                csv_keywords,
                scorer=fuzz.ratio,
                score_cutoff=_FUZZY_THRESHOLD,
            )
            if match:
                results[kw] = self._data[match[0]]
            else:
                results[kw] = None

        return results
