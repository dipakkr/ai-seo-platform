"""Data models for AI SEO Platform."""

from aiseo.models.base import create_db_and_tables, get_engine, get_session
from aiseo.models.opportunity import Opportunity
from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan

__all__ = [
    "Project",
    "Query",
    "Scan",
    "ScanResult",
    "Opportunity",
    "create_db_and_tables",
    "get_engine",
    "get_session",
]
