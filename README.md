# AI SEO Platform

**Track and optimize your brand's visibility across AI search engines**

Track how ChatGPT, Perplexity, Gemini, and Claude talk about your product — and find opportunities to get visible.

## Why?

AI search engines are the new discovery channel. If ChatGPT doesn't recommend your product when someone asks "best [your category] tools", you're invisible to a growing audience. AI SEO Platform tells you exactly where you stand — and what to fix.

## Quick Start

```bash
pip install aiseo

# Set at least one LLM API key
export AISEO_OPENAI_API_KEY=sk-...

# Scan your site
aiseo scan https://yoursite.com
```

Or run with Docker:

```bash
cp .env.example .env
# Edit .env with your API keys
docker compose up
```

Then open `http://localhost:3000` for the dashboard, or `http://localhost:8000/docs` for the API.

## Features

- **Auto Brand Detection** — paste a URL, AI SEO Platform extracts brand name, competitors, features, and category
- **Multi-LLM Scanning** — checks visibility across ChatGPT, Perplexity, Gemini, and Claude
- **AI Visibility Score** — 0-100, broken down by LLM and query intent category
- **Opportunity Engine** — prioritized visibility gaps ranked by search volume x impact
- **Search Volume** — pluggable adapters: Google Ads, SEMrush, Ahrefs, autocomplete (free), or CSV
- **Dashboard** — React + Tailwind UI for visual analysis
- **Self-Hosted** — Docker Compose, runs on your own infrastructure

## How It Works

1. **Paste URL** — AI SEO Platform scrapes your site and uses an LLM to extract brand profile, competitors, and features
2. **Generate Queries** — auto-generates 50+ buyer-intent queries across 4 categories: discovery, comparison, problem, recommendation
3. **Scan LLMs** — sends each query to configured LLM providers with web search enabled
4. **Detect Mentions** — fuzzy-matches your brand name (and aliases) in every response, extracts position, sentiment, citations
5. **Score & Rank** — computes a 0-100 visibility score weighted by search volume, surfaces actionable opportunities

## Architecture

```
URL → Brand Extractor → Query Generator → Visibility Scanner → Scorer → Opportunity Engine
                                               |
                              ┌────────────────┼────────────────┐
                              │                │                │
                          ChatGPT         Perplexity        Gemini        Claude
                        (web search)      (Sonar API)     (grounding)   (training data)
```

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI |
| Task Queue | Celery + Redis |
| Database | SQLite (default) / PostgreSQL |
| LLM SDKs | openai, anthropic, google-genai |
| NLP | spaCy + rapidfuzz |
| Frontend | React 18 + Tailwind CSS + Recharts |

## API

All endpoints are under `/api/v1`. Full OpenAPI docs at `/docs` when the server is running.

```
POST   /api/v1/projects              Create project from URL
GET    /api/v1/projects               List projects
GET    /api/v1/projects/:id           Get project with queries
PATCH  /api/v1/projects/:id           Update brand profile

POST   /api/v1/projects/:id/scan     Trigger a scan
GET    /api/v1/scans/:id              Get scan status
GET    /api/v1/scans/:id/results      Get per-query results
GET    /api/v1/scans/:id/opportunities Get ranked opportunities

GET    /api/v1/projects/:id/history   Scan history
```

## Configuration

All settings are via environment variables (prefix `AISEO_`). Copy `.env.example` to `.env`:

```bash
# LLM Provider Keys (all optional — use what you have)
AISEO_OPENAI_API_KEY=
AISEO_ANTHROPIC_API_KEY=
AISEO_GOOGLE_API_KEY=
AISEO_PERPLEXITY_API_KEY=

# Search Volume (optional)
AISEO_SEMRUSH_API_KEY=
AISEO_AHREFS_API_KEY=

# Infrastructure
AISEO_DATABASE_URL=sqlite:///aiseo.db
AISEO_REDIS_URL=redis://localhost:6379/0
```

AI SEO Platform works with whatever keys you provide. Only have an OpenAI key? It'll scan ChatGPT only. Add more keys to scan more LLMs.

## Development

```bash
# Clone and install
git clone https://github.com/anthropics/ai-seo-platform.git
cd ai-seo-platform
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Download spaCy model
python -m spacy download en_core_web_sm

# Run API server
uvicorn aiseo.main:app --reload

# Run frontend (separate terminal)
cd frontend && npm install && npm run dev

# Run tests
pytest
```

## vs Paid Tools

| Feature | AI SEO Platform | Otterly.AI ($29/mo) | GenRank ($49/mo) | SE Visible |
|---------|--------|---------------------|------------------|------------|
| Open Source | Yes | No | No | No |
| Auto Brand Detection | Yes | No | No | No |
| Auto Query Generation | Yes | No | No | No |
| Multi-LLM | 4 | 6 | 1 (ChatGPT) | 4 |
| Search Volume | Pluggable (5 sources) | No | No | No |
| Opportunity Ranking | Yes | Partial | No | Partial |
| Self-Hosted | Yes | No | No | No |
| Price | Free | $29/mo | $49/mo | Custom |

## Project Structure

```
src/aiseo/
  main.py               FastAPI app
  config.py             Settings (pydantic-settings)
  models/               SQLModel data models
  services/             Core logic (brand extractor, scanner, scorer, etc.)
  providers/            LLM integrations (ChatGPT, Perplexity, Gemini, Claude)
  volume/               Search volume adapters
  api/                  FastAPI routes
  tasks/                Celery async tasks

frontend/               React + Tailwind dashboard
```

## License

MIT
