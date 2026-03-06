"""Opportunity model - computed visibility gap."""

import json

from sqlmodel import Column, Field, SQLModel, Text


class Opportunity(SQLModel, table=True):
    """A computed opportunity representing a visibility gap."""

    id: int | None = Field(default=None, primary_key=True)
    scan_id: int = Field(foreign_key="scan.id")
    query_id: int = Field(foreign_key="query.id")
    opportunity_type: str  # "invisible" | "competitor_dominated" | "negative_sentiment" | "partial_visibility"
    impact_score: float
    visibility_gap: float  # how much more visible competitors are (0-1)
    competitors_visible_json: str = Field(default="[]", sa_column=Column(Text))
    providers_missing_json: str = Field(default="[]", sa_column=Column(Text))
    recommendation: str = ""

    @property
    def competitors_visible(self) -> list[str]:
        return json.loads(self.competitors_visible_json)

    @competitors_visible.setter
    def competitors_visible(self, value: list[str]):
        self.competitors_visible_json = json.dumps(value)

    @property
    def providers_missing(self) -> list[str]:
        return json.loads(self.providers_missing_json)

    @providers_missing.setter
    def providers_missing(self, value: list[str]):
        self.providers_missing_json = json.dumps(value)
