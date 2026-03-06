# CLAUDE.md — Open Source AI SEO Optimisation

## Project Identity

- **Name**: AI SEO Platform
- **Tagline**: AI Visibility Intelligence for SaaS Founders
- **Repo**: `ai-seo-platform`
- **License**: MIT
- **One-liner**: Track how ChatGPT, Perplexity, Gemini, and Claude talk about your product — and find opportunities to get visible.

## What This Project Does

AI SEO Platform lets a SaaS founder paste their website URL and instantly see:
1. How visible their brand is across AI search engines (ChatGPT, Perplexity, Gemini, Claude)
2. Which buyer-intent queries mention them (or don't)
3. Where competitors are visible but they're not
4. Prioritized opportunities ranked by search volume × visibility gap

The core user flow is: **Paste URL → Auto-extract brand → Auto-generate queries → Scan LLMs → Score visibility → Surface opportunities**

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Best LLM SDK ecosystem, FastAPI, spaCy |
| API Framework | FastAPI | Async-first, auto-docs, modern Python |
| CLI | Typer | Same codebase powers CLI and API |
| Task Queue | Celery + Redis | Async scan processing (400+ API calls per scan) |
| Database | SQLite (default) / PostgreSQL (optional) | Local-first, zero-config |
| LLM Providers | Direct SDKs: `openai`, `anthropic`, `google-genai`, `perplexity` | No abstraction layer overhead, full control per provider |
| NLP | spaCy (en_core_web_sm) + rapidfuzz | Brand mention detection, entity extraction |
| Search Volume | Adapter pattern (autocomplete scraper as free default) | Pluggable: Google Ads, SEMrush, Ahrefs, CSV |
| Frontend | React 18 + Tailwind CSS + Recharts | Dashboard (separate package, optional) |
| Deployment | Docker Compose | One-command self-hosted setup |

## Project Structure

```
ai-seo-platform/
├── CLAUDE.md                    # This file — project blueprint
├── README.md                    # Public-facing docs
├── pyproject.toml               # Python package config (use hatchling)
├── docker-compose.yml           # Redis + GEOkit + optional Postgres
├── Dockerfile
├── .env.example                 # All BYOK API keys
│
├── src/
│   └── aiseo/
│       ├── __init__.py
│       ├── main.py              # FastAPI app factory
│       ├── cli.py               # Typer CLI entry point
│       ├── config.py            # Settings via pydantic-settings, loads .env
│       │
│       ├── models/              # SQLAlchemy / SQLModel data models
│       │   ├── __init__.py
│       │   ├── project.py       # Project (brand profile + settings)
│       │   ├── query.py         # Generated queries with metadata
│       │   ├── scan.py          # Scan run (timestamp, status, config)
│       │   ├── result.py        # Per-query, per-LLM scan result
│       │   └── opportunity.py   # Computed opportunity with impact score
│       │
│       ├── services/            # Core business logic
│       │   ├── __init__.py
│       │   ├── brand_extractor.py    # URL → brand profile
│       │   ├── query_generator.py    # Brand profile → query set
│       │   ├── visibility_scanner.py # Orchestrates LLM scanning
│       │   ├── mention_detector.py   # Fuzzy brand matching in responses
│       │   ├── citation_parser.py    # Extract URLs cited by LLMs
│       │   ├── scorer.py             # Compute AI Visibility Score (0-100)
│       │   └── opportunity_engine.py # Rank gaps by impact
│       │
│       ├── providers/           # LLM provider integrations
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract LLMProvider class
│       │   ├── chatgpt.py       # OpenAI Responses API + web_search
│       │   ├── perplexity.py    # Sonar API (answers) + Search API (raw)
│       │   ├── gemini.py        # Google GenAI + Search grounding
│       │   └── claude.py        # Anthropic Messages API (no web search)
│       │
│       ├── volume/              # Search volume adapters
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract SearchVolumeAdapter
│       │   ├── autocomplete.py  # Google/Bing autocomplete scraper (FREE)
│       │   ├── google_ads.py    # Google Keyword Planner API
│       │   ├── semrush.py       # SEMrush API
│       │   ├── ahrefs.py        # Ahrefs API
│       │   └── csv_upload.py    # User-provided CSV
│       │
│       ├── api/                 # FastAPI routes
│       │   ├── __init__.py
│       │   ├── projects.py      # CRUD for projects
│       │   ├── scans.py         # Trigger and monitor scans
│       │   ├── results.py       # Fetch scan results
│       │   └── opportunities.py # Fetch ranked opportunities
│       │
│       ├── tasks/               # Celery async tasks
│       │   ├── __init__.py
│       │   └── scan_task.py     # Main scan orchestration task
│       │
│       └── utils/
│           ├── __init__.py
│           ├── scraper.py       # Website content extraction (httpx + BeautifulSoup)
│           └── text.py          # Text processing helpers
│
├── frontend/                    # React dashboard (separate, optional)
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ProjectSetup.jsx
│   │   │   ├── ScanResults.jsx
│   │   │   └── Opportunities.jsx
│   │   └── components/
│   │       ├── VisibilityScore.jsx
│   │       ├── LLMBreakdown.jsx
│   │       ├── CompetitorChart.jsx
│   │       └── OpportunityTable.jsx
│   └── ...
│
└── tests/
    ├── test_brand_extractor.py
    ├── test_query_generator.py
    ├── test_mention_detector.py
    ├── test_scorer.py
    └── test_providers/
        ├── test_chatgpt.py
        ├── test_perplexity.py
        ├── test_gemini.py
        └── test_claude.py
```

## Implementation Guide

### Phase 1: Foundation (Week 1)

#### 1.1 Project Setup

```bash
# Use hatchling for modern Python packaging
# Python 3.11+, use pyproject.toml (no setup.py)
```

**pyproject.toml dependencies:**
```toml
[project]
name = "geokit"
version = "0.1.0"
description = "AI Visibility Intelligence for SaaS Founders"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "typer[all]>=0.12.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "sqlmodel>=0.0.22",
    "pydantic-settings>=2.6.0",
    "openai>=1.60.0",
    "anthropic>=0.40.0",
    "google-genai>=1.0.0",
    "spacy>=3.8.0",
    "rapidfuzz>=3.10.0",
    "celery[redis]>=5.4.0",
    "rich>=13.9.0",
    "textstat>=0.7.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio", "ruff", "mypy"]
semrush = ["semrush-api"]  # optional paid integration
postgres = ["asyncpg", "psycopg2-binary"]

[project.scripts]
geokit = "geokit.cli:app"
```

#### 1.2 Config (`src/aiseo/config.py`)

Use pydantic-settings to load from `.env`. All API keys are optional — the tool works with whatever keys the user provides.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Provider Keys (all optional — BYOK)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    perplexity_api_key: str | None = None

    # Search Volume Keys (all optional)
    google_ads_developer_token: str | None = None
    google_ads_client_id: str | None = None
    semrush_api_key: str | None = None
    ahrefs_api_key: str | None = None

    # Infrastructure
    database_url: str = "sqlite:///geokit.db"
    redis_url: str = "redis://localhost:6379/0"

    # Scan defaults
    default_query_count: int = 50
    max_queries_per_scan: int = 200
    scan_timeout_seconds: int = 300

    model_config = {"env_file": ".env", "env_prefix": "GEOKIT_"}
```

#### 1.3 Data Models (`src/aiseo/models/`)

Use SQLModel (SQLAlchemy + Pydantic hybrid). Key models:

**Project** — represents one brand being tracked:
```python
class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str                          # input URL
    brand_name: str                   # extracted brand name
    brand_aliases: list[str] = []     # e.g. ["PostZaper", "Post Zaper", "postzaper.com"]
    description: str = ""             # auto-extracted product description
    category: str = ""                # e.g. "project management", "social media automation"
    competitors: list[str] = []       # auto-detected competitor names
    features: list[str] = []          # key product features
    target_audience: str = ""         # e.g. "SaaS founders", "marketers"
    created_at: datetime
    updated_at: datetime
```

**Query** — a single query to check visibility for:
```python
class Query(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    text: str                         # the actual query string
    intent_category: str              # "discovery" | "comparison" | "problem" | "recommendation"
    search_volume: int | None = None  # from search volume adapter
    volume_source: str | None = None  # "google_ads" | "semrush" | "autocomplete" | "csv"
    is_active: bool = True            # user can disable queries
```

**ScanResult** — one query × one LLM result:
```python
class ScanResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scan_id: int = Field(foreign_key="scan.id")
    query_id: int = Field(foreign_key="query.id")
    provider: str                     # "chatgpt" | "perplexity" | "gemini" | "claude"
    raw_response: str                 # full LLM response text
    brand_mentioned: bool             # was the brand found?
    brand_position: int | None        # position in list (1st, 2nd, 3rd...) if applicable
    brand_sentiment: str | None       # "positive" | "neutral" | "negative"
    brand_context: str | None         # excerpt around the brand mention
    competitors_mentioned: list[str] = []  # other brands found in response
    citations: list[str] = []         # URLs cited by the LLM
    brand_cited: bool = False         # was OUR domain in the citations?
    response_tokens: int | None = None
    latency_ms: int | None = None
```

**Opportunity** — computed gap:
```python
class Opportunity(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scan_id: int = Field(foreign_key="scan.id")
    query_id: int = Field(foreign_key="query.id")
    opportunity_type: str             # "invisible" | "competitor_dominated" | "negative_sentiment" | "partial_visibility"
    impact_score: float               # search_volume × visibility_gap
    visibility_gap: float             # how much more visible competitors are (0-1)
    competitors_visible: list[str]    # who IS visible for this query
    providers_missing: list[str]      # which LLMs don't mention you
    recommendation: str               # actionable text recommendation
```

#### 1.4 Brand Extractor (`src/aiseo/services/brand_extractor.py`)

This is the magic onboarding step. Input: URL. Output: complete brand profile.

```python
async def extract_brand_profile(url: str, llm_client) -> Project:
    """
    1. Fetch the URL with httpx
    2. Extract: title, meta description, OG tags, h1/h2, about page link
    3. If about page exists, fetch that too
    4. Send extracted text to LLM with structured output prompt
    5. Return populated Project
    """
```

**LLM prompt for extraction** (use structured JSON output):
```
You are analyzing a SaaS product website. Extract the following as JSON:
{
  "brand_name": "exact product/company name",
  "brand_aliases": ["common variations, abbreviations, domain name"],
  "description": "one-paragraph product description",
  "category": "product category (e.g., 'project management', 'email marketing')",
  "competitors": ["up to 5 likely competitors based on category"],
  "features": ["top 5 key features"],
  "target_audience": "primary user persona"
}

Website content:
<content>{scraped_text}</content>
```

Use whichever LLM key the user has configured. Preference order: OpenAI > Anthropic > Gemini.

#### 1.5 Query Generator (`src/aiseo/services/query_generator.py`)

Generates buyer-intent queries from the brand profile. Four intent categories:

```python
INTENT_TEMPLATES = {
    "discovery": [
        "best {category} tools",
        "best {category} tools {year}",
        "top {category} software",
        "best {category} for {audience}",
        "{category} tools for startups",
    ],
    "comparison": [
        "{brand} vs {competitor}",
        "{brand} alternatives",
        "{brand} review",
        "is {brand} good",
        "{brand} vs {competitor} which is better",
    ],
    "problem": [
        "how to {problem_verb} {problem_noun}",
        "best way to {problem_verb} {problem_noun}",
        "tools for {problem_noun}",
    ],
    "recommendation": [
        "which {category} should I use",
        "what {category} do you recommend",
        "recommend a {category} for {use_case}",
    ],
}
```

Also use LLM to generate additional queries beyond templates:
```
Given this SaaS product profile, generate 30 additional queries that a potential 
buyer might type into ChatGPT or Perplexity when looking for a solution like this.

Focus on:
- Natural conversational queries (how people actually talk to AI)
- Problem-aware queries (they know the problem, not the solution)
- Comparison queries (evaluating options)
- Use-case specific queries

Product: {brand_profile_json}

Return as JSON array of objects: [{"text": "query", "intent_category": "discovery|comparison|problem|recommendation"}]
```

### Phase 2: LLM Visibility Scanning (Week 2)

#### 2.1 Provider Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMResponse:
    text: str                    # full response text
    citations: list[str]         # URLs cited
    model: str                   # model name used
    tokens_used: int | None
    latency_ms: int

class LLMProvider(ABC):
    name: str  # "chatgpt" | "perplexity" | "gemini" | "claude"

    @abstractmethod
    async def query(self, prompt: str) -> LLMResponse:
        """Send a query and return structured response."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API key is set."""
        pass
```

#### 2.2 ChatGPT Provider (`providers/chatgpt.py`)

Use OpenAI Responses API with web_search tool:

```python
from openai import AsyncOpenAI

class ChatGPTProvider(LLMProvider):
    name = "chatgpt"

    async def query(self, prompt: str) -> LLMResponse:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.responses.create(
            model="gpt-4o-mini",  # cost-efficient for high-volume scans
            tools=[{"type": "web_search"}],
            input=prompt,
        )
        # Extract text from output
        text = response.output_text

        # Extract citations from annotations
        citations = []
        for item in response.output:
            if hasattr(item, 'content'):
                for block in item.content:
                    if hasattr(block, 'annotations'):
                        for ann in block.annotations:
                            if ann.type == "url_citation":
                                citations.append(ann.url)

        return LLMResponse(
            text=text,
            citations=list(set(citations)),
            model="gpt-4o-mini",
            tokens_used=response.usage.total_tokens if response.usage else None,
            latency_ms=...,
        )
```

#### 2.3 Perplexity Provider (`providers/perplexity.py`)

Use Sonar API for AI-generated answers with citations:

```python
from openai import AsyncOpenAI  # Perplexity uses OpenAI-compatible API

class PerplexityProvider(LLMProvider):
    name = "perplexity"

    async def query(self, prompt: str) -> LLMResponse:
        client = AsyncOpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai",
        )
        response = await client.chat.completions.create(
            model="sonar",  # or "sonar-pro" for better quality
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content

        # Perplexity Sonar returns citations in the response
        # Parse [1], [2] style citations and extract URLs
        citations = self._extract_citations(response)

        return LLMResponse(text=text, citations=citations, ...)
```

#### 2.4 Gemini Provider (`providers/gemini.py`)

Use Google GenAI with search grounding:

```python
from google import genai

class GeminiProvider(LLMProvider):
    name = "gemini"

    async def query(self, prompt: str) -> LLMResponse:
        client = genai.Client(api_key=settings.google_api_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                tools=[genai.types.Tool(
                    google_search=genai.types.GoogleSearchRetrieval()
                )]
            ),
        )
        text = response.text

        # Extract grounding sources
        citations = []
        if response.candidates[0].grounding_metadata:
            for source in response.candidates[0].grounding_metadata.grounding_chunks:
                if hasattr(source, 'web') and source.web.uri:
                    citations.append(source.web.uri)

        return LLMResponse(text=text, citations=citations, ...)
```

#### 2.5 Claude Provider (`providers/claude.py`)

Claude API has no web search — useful for checking training data presence:

```python
from anthropic import AsyncAnthropic

class ClaudeProvider(LLMProvider):
    name = "claude"

    async def query(self, prompt: str) -> LLMResponse:
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        # No citations — Claude doesn't do web search via API
        return LLMResponse(text=text, citations=[], ...)
```

#### 2.6 Mention Detector (`services/mention_detector.py`)

Critical component — must handle brand name variants fuzzy matching:

```python
from rapidfuzz import fuzz, process

class MentionDetector:
    def __init__(self, brand_name: str, brand_aliases: list[str]):
        self.targets = [brand_name.lower()] + [a.lower() for a in brand_aliases]

    def detect(self, text: str) -> MentionResult:
        """
        1. Exact match (case-insensitive) for each alias
        2. Fuzzy match with rapidfuzz (threshold: 85) for typos/variations
        3. Find position — if response lists tools, what position is the brand?
        4. Extract context — 200 chars around the mention
        5. Basic sentiment — positive/negative/neutral via keyword heuristics
           (or LLM call if budget allows)
        """
        text_lower = text.lower()

        # Exact match
        mentioned = any(t in text_lower for t in self.targets)

        # Fuzzy match fallback
        if not mentioned:
            words = text_lower.split()
            for target in self.targets:
                match = process.extractOne(target, words, scorer=fuzz.ratio)
                if match and match[1] >= 85:
                    mentioned = True
                    break

        # Position detection — find numbered/bulleted lists
        position = self._detect_position(text, self.targets)

        # Context extraction
        context = self._extract_context(text, self.targets, window=200)

        # Competitor extraction — find other brand-like entities
        competitors = self._extract_other_brands(text, self.targets)

        return MentionResult(
            mentioned=mentioned,
            position=position,
            context=context,
            sentiment=self._basic_sentiment(context),
            competitors_mentioned=competitors,
        )
```

#### 2.7 Visibility Scanner Orchestrator (`services/visibility_scanner.py`)

Orchestrates the full scan — this runs as a Celery task:

```python
async def run_scan(project_id: int, scan_id: int):
    """
    1. Load project and active queries
    2. Determine which providers are configured
    3. For each query × each provider (in parallel, with rate limiting):
       a. Send query to LLM
       b. Run mention detector on response
       c. Parse citations
       d. Save ScanResult
    4. After all results: compute visibility scores
    5. Run opportunity engine
    6. Update scan status to "completed"
    """
    project = get_project(project_id)
    queries = get_active_queries(project_id)
    providers = get_configured_providers()  # only providers with API keys

    detector = MentionDetector(project.brand_name, project.brand_aliases)

    # Use asyncio.gather with semaphore for rate limiting
    semaphore = asyncio.Semaphore(10)  # max 10 concurrent API calls

    async def scan_one(query, provider):
        async with semaphore:
            response = await provider.query(query.text)
            mention = detector.detect(response.text)
            # Save ScanResult to DB
            ...

    tasks = [
        scan_one(q, p) for q in queries for p in providers
    ]
    await asyncio.gather(*tasks)

    # Compute scores and opportunities
    compute_visibility_scores(scan_id)
    compute_opportunities(scan_id, project)
```

### Phase 3: Scoring + Search Volume (Week 3)

#### 3.1 AI Visibility Score (`services/scorer.py`)

Score formula (0-100):

```python
def compute_visibility_score(scan_results: list[ScanResult]) -> VisibilityScore:
    """
    Per-query score:
      mention_score = 1 if mentioned, 0 if not (per LLM)
      position_bonus = 1.0 if pos 1, 0.7 if pos 2, 0.5 if pos 3, 0.3 if pos 4+
      citation_bonus = 0.2 if brand's domain is in citations
      sentiment_modifier = 1.0 if positive, 0.7 if neutral, 0.3 if negative

      query_score = mention_score × (position_bonus + citation_bonus) × sentiment_modifier

    Overall score:
      weighted_sum = Σ (query_score × query_importance) / Σ query_importance
      query_importance = search_volume if available, else 1.0

    Normalize to 0-100 scale.

    Also compute:
      - per_llm_score: {chatgpt: 72, perplexity: 45, gemini: 60, claude: 30}
      - per_category_score: {discovery: 40, comparison: 80, problem: 20, recommendation: 55}
      - competitor_scores: {competitor_a: 85, competitor_b: 60}
    """
```

#### 3.2 Search Volume Adapters

**Base class:**
```python
class SearchVolumeAdapter(ABC):
    name: str

    @abstractmethod
    async def get_volumes(self, keywords: list[str]) -> dict[str, int | None]:
        """Return {keyword: monthly_search_volume} dict."""
        pass
```

**Autocomplete adapter (FREE default):**
```python
class AutocompleteAdapter(SearchVolumeAdapter):
    """
    Scrape Google autocomplete suggestions as a demand proxy.
    More suggestions = higher relative demand.
    Not exact volume, but good for ranking/prioritization.

    GET https://suggestqueries.google.com/complete/search?client=firefox&q={keyword}

    Returns number of suggestions as a proxy score (0-10).
    Can also check if the keyword appears in Bing autocomplete for cross-validation.
    """
```

**Google Keyword Planner adapter:**
```python
class GoogleAdsAdapter(SearchVolumeAdapter):
    """
    Uses google-ads Python client library.
    Requires: developer token, client ID, client secret, refresh token.
    Returns exact monthly search volumes.
    Batch queries in groups of 200 (API limit).
    """
```

**CSV upload adapter:**
```python
class CSVAdapter(SearchVolumeAdapter):
    """
    Accept CSV with columns: keyword, volume
    Map to our query texts using fuzzy matching.
    """
```

#### 3.3 Opportunity Engine (`services/opportunity_engine.py`)

```python
def compute_opportunities(scan_id: int, project: Project) -> list[Opportunity]:
    """
    For each query, compare brand visibility vs competitor visibility:

    Types:
    1. "invisible" — brand not mentioned on ANY LLM, but competitors are
       → highest priority, these are blind spots
    2. "competitor_dominated" — brand mentioned but lower position than competitor
       → optimize content for these queries
    3. "partial_visibility" — mentioned on some LLMs but not others
       → quick wins, figure out why some LLMs miss you
    4. "negative_sentiment" — brand mentioned but negatively
       → reputation risk, needs content cleanup

    Impact score = search_volume × visibility_gap
    where visibility_gap = avg_competitor_visibility - brand_visibility (0 to 1)

    Sort all opportunities by impact_score descending.
    Generate actionable recommendation text for each.
    """
```

**Recommendation templates:**
```python
RECOMMENDATIONS = {
    "invisible": "Your brand is invisible for '{query}' across {providers}. "
                 "Competitors like {competitors} are being recommended instead. "
                 "Consider: create a dedicated page targeting this query, "
                 "get listed in comparison articles, ensure structured data coverage.",
    "competitor_dominated": "You appear for '{query}' but {competitor} is recommended first. "
                            "Strengthen your positioning by adding statistics, citations, "
                            "and comparison content on your site.",
    "partial_visibility": "You're visible on {visible_providers} but missing from {missing_providers}. "
                          "Check that your content is indexed by the missing platforms. "
                          "Ensure Bing indexing (ChatGPT relies on Bing).",
    "negative_sentiment": "Your brand is mentioned for '{query}' but in a negative context. "
                          "Review the AI's sources and address any outdated/inaccurate information.",
}
```

### Phase 4: API + Dashboard (Week 4)

#### 4.1 FastAPI Routes

```
POST   /api/v1/projects              # Create project from URL
GET    /api/v1/projects/:id           # Get project details
PATCH  /api/v1/projects/:id           # Update brand profile / queries

POST   /api/v1/projects/:id/scan      # Trigger a new scan
GET    /api/v1/scans/:id              # Get scan status + results
GET    /api/v1/scans/:id/results      # Detailed per-query results
GET    /api/v1/scans/:id/opportunities # Ranked opportunity list

GET    /api/v1/projects/:id/queries   # List all queries
POST   /api/v1/projects/:id/queries   # Add queries manually
DELETE /api/v1/queries/:id            # Remove a query

GET    /api/v1/projects/:id/history   # Historical scan scores
```

#### 4.2 CLI Commands

```bash
# Quick scan (one-shot)
geokit scan https://postzaper.com

# Project management
geokit project create https://postzaper.com
geokit project show 1
geokit project queries 1 --add "best social media scheduler"

# Run scan
geokit scan run 1 --providers chatgpt,perplexity,gemini

# View results
geokit results 1 --format table
geokit opportunities 1 --top 10

# Search volume enrichment
geokit enrich 1 --source autocomplete
geokit enrich 1 --source csv --file keywords.csv

# Server mode
geokit serve --port 8000
```

#### 4.3 React Dashboard Pages

**Dashboard (main view):**
- AI Visibility Score gauge (0-100) with trend arrow
- Per-LLM breakdown bars (ChatGPT: 72, Perplexity: 45, etc.)
- Top 5 opportunities list
- Recent scan history sparkline

**Project Setup:**
- URL input → shows auto-extracted brand profile (editable)
- Query list with checkboxes, intent category tags, volume data
- Provider selection (which LLMs to scan)
- "Run Scan" button

**Scan Results:**
- Filterable table: query | chatgpt | perplexity | gemini | claude | volume
- Each cell shows: ✅ mentioned (green) / ❌ missing (red) / ⚠️ negative (yellow)
- Click a cell to see full LLM response with brand mention highlighted
- Export as CSV

**Opportunities:**
- Sorted by impact score
- Each card shows: query, opportunity type, impact score, which competitors ARE visible, which LLMs miss you, recommendation
- Filter by type (invisible / competitor_dominated / partial / negative)

### Phase 5: Polish + Launch (Week 5-6)

#### 5.1 README Structure

```markdown
# GEOkit ⚡

**AI Visibility Intelligence for SaaS Founders**

Track how ChatGPT, Perplexity, Gemini, and Claude talk about your product.

[Demo GIF here — terminal showing: geokit scan https://example.com → scores → opportunities]

## Why?

AI search engines are the new discovery channel. If ChatGPT doesn't recommend 
your product when someone asks "best [your category] tools", you're invisible 
to a growing audience. GEOkit tells you exactly where you stand — and what to fix.

## Quick Start

\`\`\`bash
pip install geokit
geokit scan https://yoursite.com
\`\`\`

## Features

- 🔍 **Auto Brand Detection** — paste a URL, GEOkit extracts everything
- 🤖 **Multi-LLM Scanning** — ChatGPT, Perplexity, Gemini, Claude
- 📊 **AI Visibility Score** — 0-100, broken down by LLM and query type
- 🎯 **Opportunity Engine** — prioritized gaps ranked by search volume
- 📈 **Search Volume** — Google Ads, SEMrush, Ahrefs, or free autocomplete
- 🖥️ **Dashboard** — React UI for visual analysis (optional)
- 🐳 **Self-Hosted** — Docker Compose, runs on your own infra

## vs Paid Tools

| Feature | GEOkit | Otterly.AI ($29/mo) | GenRank | SE Visible |
|---------|--------|---------------------|---------|------------|
| Open Source | ✅ | ❌ | ❌ | ❌ |
| Auto Brand Detection | ✅ | ❌ | ❌ | ❌ |
| Auto Query Generation | ✅ | ❌ | ❌ | ❌ |
| Multi-LLM | 4 | 6 | 1 (ChatGPT) | 4 |
| Search Volume | Pluggable (5 sources) | ❌ | ❌ | ❌ |
| Opportunity Ranking | ✅ | Partial | ❌ | Partial |
| Self-Hosted | ✅ | ❌ | ❌ | ❌ |
| Price | Free | $29/mo | $49/mo | Custom |
```

#### 5.2 Docker Compose

```yaml
version: '3.8'
services:
  geokit:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - redis
    command: geokit serve --port 8000

  worker:
    build: .
    env_file: .env
    depends_on:
      - redis
    command: celery -A geokit.tasks worker --loglevel=info

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Optional: dashboard
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
```

#### 5.3 MCP Server (for Claude Code / Cursor users)

Create a simple MCP server that exposes GEOkit tools:
```
Tools:
- geokit_scan(url) → runs a quick scan and returns visibility score
- geokit_opportunities(url) → returns top opportunities
- geokit_check(brand, query) → checks one brand × one query across LLMs
```

This lets developers check their AI visibility from inside their AI coding tool. Very meta, very shareable.

#### 5.4 Free Public Scanner

A web page at geokit.dev/scan:
- Input: URL
- Limited: 10 queries, 2 LLMs (ChatGPT + Perplexity)
- Output: shareable report page with visibility score
- CTA: "Want full scan? Self-host GEOkit (free) or upgrade to Pro"

This is the primary viral distribution mechanism.

## Code Style Rules

- Python: Use `ruff` for linting/formatting. Type hints everywhere. Async by default.
- Imports: Use absolute imports (`from geokit.services.scorer import ...`)
- Error handling: Never let one failed LLM call crash the scan. Log and continue.
- Logging: Use `structlog` for structured JSON logging.
- Tests: Every service has unit tests. Mock LLM calls in tests.
- Docstrings: Google style docstrings on all public functions.
- Config: All settings via environment variables. No hardcoded keys or secrets.

## Critical Implementation Notes

1. **Rate limiting is essential.** OpenAI has rate limits. Perplexity has rate limits. Use `asyncio.Semaphore` and implement exponential backoff with `tenacity`.

2. **Cost awareness.** A scan of 100 queries × 4 LLMs = 400 API calls. With GPT-4o-mini + web search, that's roughly $2-5. Show estimated cost before scan starts. Offer "quick scan" (10 queries, 2 LLMs) as default.

3. **Caching.** LLM responses are non-deterministic, but for development/testing, cache responses to avoid burning API credits. Use simple file-based cache keyed on (provider, query, date).

4. **Graceful degradation.** If user only has OpenAI key, scan only ChatGPT. Never fail because a provider isn't configured — just skip it and note it in results.

5. **Progress reporting.** Scans take 2-5 minutes. Must show progress via CLI (rich progress bar) and API (SSE or polling endpoint).

## Launch Checklist

- [ ] README with demo GIF
- [ ] `pip install geokit` works (publish to PyPI)
- [ ] `geokit scan <url>` works end-to-end with just an OpenAI key
- [ ] Docker Compose works with one command
- [ ] Dashboard shows results visually
- [ ] Free public scanner page deployed
- [ ] Comparison table vs paid tools in README
- [ ] Submit to: Product Hunt, Hacker News (Show HN), r/SaaS, r/SEO, r/artificial
- [ ] List on awesome-generative-engine-optimization GitHub list
- [ ] Cross-promote on ToolJunction (blog + listing)
- [ ] Tweet thread with scan results of popular SaaS tools