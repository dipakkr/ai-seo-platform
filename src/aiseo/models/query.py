"""Query model - a single query to check visibility for."""

from sqlmodel import Field, SQLModel


class Query(SQLModel, table=True):
    """A search query associated with a project."""

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    text: str
    intent_category: str  # "discovery" | "comparison" | "problem" | "recommendation"
    search_volume: int | None = None
    volume_source: str | None = None  # "google_ads" | "semrush" | "autocomplete" | "csv"
    is_active: bool = True
