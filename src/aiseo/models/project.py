"""Project model - represents one brand being tracked."""

import json
from datetime import datetime, timezone

from sqlmodel import Column, Field, SQLModel, Text


class Project(SQLModel, table=True):
    """A brand/product being tracked for AI visibility."""

    id: int | None = Field(default=None, primary_key=True)
    url: str
    brand_name: str
    brand_aliases_json: str = Field(default="[]", sa_column=Column(Text))
    description: str = ""
    category: str = ""
    competitors_json: str = Field(default="[]", sa_column=Column(Text))
    features_json: str = Field(default="[]", sa_column=Column(Text))
    target_audience: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def brand_aliases(self) -> list[str]:
        return json.loads(self.brand_aliases_json)

    @brand_aliases.setter
    def brand_aliases(self, value: list[str]):
        self.brand_aliases_json = json.dumps(value)

    @property
    def competitors(self) -> list[str]:
        return json.loads(self.competitors_json)

    @competitors.setter
    def competitors(self, value: list[str]):
        self.competitors_json = json.dumps(value)

    @property
    def features(self) -> list[str]:
        return json.loads(self.features_json)

    @features.setter
    def features(self, value: list[str]):
        self.features_json = json.dumps(value)
