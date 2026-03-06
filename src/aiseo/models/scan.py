"""Scan model - a scan run with timestamp, status, and config."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Scan(SQLModel, table=True):
    """A single scan execution against a project's queries."""

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    status: str = "pending"  # "pending" | "running" | "completed" | "failed"
    providers_used: str = ""  # comma-separated: "chatgpt,perplexity,gemini,claude"
    total_queries: int = 0
    completed_queries: int = 0
    visibility_score: float | None = None
    error_message: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
