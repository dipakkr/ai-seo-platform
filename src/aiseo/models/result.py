"""ScanResult model - one query x one LLM result."""

import json

from sqlmodel import Column, Field, SQLModel, Text


class ScanResult(SQLModel, table=True):
    """Result of scanning one query against one LLM provider."""

    __tablename__ = "scan_result"

    id: int | None = Field(default=None, primary_key=True)
    scan_id: int = Field(foreign_key="scan.id")
    query_id: int = Field(foreign_key="query.id")
    provider: str  # "chatgpt" | "perplexity" | "gemini" | "claude"
    raw_response: str = Field(default="", sa_column=Column(Text))
    brand_mentioned: bool = False
    brand_position: int | None = None
    brand_sentiment: str | None = None  # "positive" | "neutral" | "negative"
    brand_context: str | None = None
    competitors_mentioned_json: str = Field(default="[]", sa_column=Column(Text))
    citations_json: str = Field(default="[]", sa_column=Column(Text))
    brand_cited: bool = False
    brands_ranked_json: str = Field(default="[]", sa_column=Column(Text))
    response_tokens: int | None = None
    latency_ms: int | None = None

    @property
    def competitors_mentioned(self) -> list[str]:
        return json.loads(self.competitors_mentioned_json)

    @competitors_mentioned.setter
    def competitors_mentioned(self, value: list[str]):
        self.competitors_mentioned_json = json.dumps(value)

    @property
    def citations(self) -> list[str]:
        return json.loads(self.citations_json)

    @citations.setter
    def citations(self, value: list[str]):
        self.citations_json = json.dumps(value)

    @property
    def brands_ranked(self) -> list[dict]:
        return json.loads(self.brands_ranked_json)

    @brands_ranked.setter
    def brands_ranked(self, value: list[dict]):
        self.brands_ranked_json = json.dumps(value)
