"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    """Optional body for scan trigger — lets the caller pick which providers to run."""
    providers: list[str] | None = None  # e.g. ["chatgpt", "perplexity"]; None = all configured


class ProjectCreateRequest(BaseModel):
    """Request body to create a project from a URL."""
    url: str


class ProjectUpdateRequest(BaseModel):
    """Partial update for a project's brand profile."""
    brand_name: str | None = None
    description: str | None = None
    category: str | None = None
    target_audience: str | None = None
    brand_aliases: list[str] | None = None
    competitors: list[str] | None = None
    features: list[str] | None = None


class QueryCreateRequest(BaseModel):
    """Request body to add a custom query."""
    text: str
    intent_category: str = "discovery"
    search_volume: int | None = None


class QueryUpdateRequest(BaseModel):
    """Partial update for a query."""
    text: str | None = None
    intent_category: str | None = None
    search_volume: int | None = None
    is_active: bool | None = None


class QueryResponse(BaseModel):
    """A single query in API responses."""
    id: int
    project_id: int
    text: str
    intent_category: str
    search_volume: int | None = None
    volume_source: str | None = None
    is_active: bool = True


class ProjectResponse(BaseModel):
    """Full project representation in API responses."""
    id: int
    url: str
    brand_name: str
    brand_aliases: list[str] = Field(default_factory=list)
    description: str = ""
    category: str = ""
    competitors: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    target_audience: str = ""
    created_at: datetime
    updated_at: datetime
    queries: list[QueryResponse] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    """Lightweight project listing (no queries)."""
    id: int
    url: str
    brand_name: str
    category: str = ""
    created_at: datetime


# ---------------------------------------------------------------------------
# Scan schemas
# ---------------------------------------------------------------------------

class ScanTriggerResponse(BaseModel):
    """Response after triggering a scan."""
    scan_id: int
    status: str
    message: str = ""


class ScanResponse(BaseModel):
    """Scan status and metadata."""
    id: int
    project_id: int
    status: str
    providers_used: str = ""
    total_queries: int = 0
    completed_queries: int = 0
    visibility_score: float | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# ScanResult schemas
# ---------------------------------------------------------------------------

class ScanResultResponse(BaseModel):
    """A single scan result row."""
    id: int
    scan_id: int
    query_id: int
    query_text: str | None = None
    provider: str
    raw_response: str = ""
    brand_mentioned: bool = False
    brand_position: int | None = None
    brand_sentiment: str | None = None
    brand_context: str | None = None
    competitors_mentioned: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    brand_cited: bool = False
    brands_ranked: list[BrandRankingEntry] = Field(default_factory=list)
    response_tokens: int | None = None
    latency_ms: int | None = None


# ---------------------------------------------------------------------------
# Opportunity schemas
# ---------------------------------------------------------------------------

class SingleQueryResultResponse(BaseModel):
    """Result of scanning a single query across all providers."""
    provider: str
    raw_response: str = ""
    brand_mentioned: bool = False
    brand_position: int | None = None
    brand_sentiment: str | None = None
    brand_context: str | None = None
    competitors_mentioned: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    brand_cited: bool = False
    brands_ranked: list[BrandRankingEntry] = Field(default_factory=list)
    latency_ms: int | None = None
    error: bool = False


class SingleQueryScanResponse(BaseModel):
    """Response for a single-query scan."""
    query_id: int
    query_text: str
    results: list[SingleQueryResultResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Brand Rankings schemas
# ---------------------------------------------------------------------------

class BrandRankingEntry(BaseModel):
    """A single brand extracted from an LLM response."""
    name: str
    position: int | None = None
    is_your_brand: bool = False


class AggregatedBrandRank(BaseModel):
    """Brand ranking aggregated across providers."""
    name: str
    avg_position: float
    mention_count: int
    providers: list[str] = Field(default_factory=list)
    is_your_brand: bool = False


class QueryRankingsResponse(BaseModel):
    """Rankings for a single query across all providers."""
    query_id: int
    query_text: str
    intent_category: str
    search_volume: int | None = None
    rankings: list[AggregatedBrandRank] = Field(default_factory=list)
    per_provider: dict[str, list[BrandRankingEntry]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Integrations schemas
# ---------------------------------------------------------------------------

class IntegrationTestRequest(BaseModel):
    """Request body for testing a provider integration."""
    provider: str  # "chatgpt" | "perplexity" | "gemini" | "claude"


class IntegrationTestResponse(BaseModel):
    """Result of a provider integration test."""
    provider: str
    configured: bool
    success: bool
    model: str | None = None
    latency_ms: int | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Opportunity schemas
# ---------------------------------------------------------------------------

class OpportunityResponse(BaseModel):
    """A single opportunity row."""
    id: int
    scan_id: int
    query_id: int
    query_text: str | None = None
    opportunity_type: str
    impact_score: float
    visibility_gap: float
    competitors_visible: list[str] = Field(default_factory=list)
    providers_missing: list[str] = Field(default_factory=list)
    recommendation: str = ""
