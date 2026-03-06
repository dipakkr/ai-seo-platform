"""Orchestrates LLM visibility scanning for a project."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlmodel import Session, select

from aiseo.models.base import get_engine
from aiseo.models.project import Project
from aiseo.models.query import Query
from aiseo.models.result import ScanResult
from aiseo.models.scan import Scan
from aiseo.providers.base import LLMProvider
from aiseo.services.brand_ranker import extract_brands
from aiseo.services.citation_parser import parse_citations
from aiseo.services.mention_detector import MentionDetector

logger = logging.getLogger(__name__)


def _get_configured_providers() -> list[LLMProvider]:
    """Return provider instances for every configured API key.

    Uses lazy imports so provider modules (which pull in heavy SDKs)
    are only loaded when actually needed and can be built in parallel.
    """
    providers: list[LLMProvider] = []

    from aiseo.providers.chatgpt import ChatGPTProvider
    from aiseo.providers.claude import ClaudeProvider
    from aiseo.providers.gemini import GeminiProvider
    from aiseo.providers.perplexity import PerplexityProvider

    for provider in (
        ChatGPTProvider(),
        PerplexityProvider(),
        GeminiProvider(),
        ClaudeProvider(),
    ):
        if provider.is_configured():
            providers.append(provider)

    return providers


def _extract_brand_domain(project: Project) -> str:
    """Extract the bare domain from the project URL."""
    parsed = urlparse(project.url)
    host = parsed.hostname or ""
    # Strip leading 'www.'
    if host.startswith("www."):
        host = host[4:]
    return host


async def run_scan(project_id: int, scan_id: int) -> None:
    """Run a full visibility scan for a project.

    Loads the project and its active queries, determines which LLM
    providers are configured, then queries every (query, provider) pair
    in parallel (capped by a semaphore).  Results are analysed with the
    MentionDetector and citation parser, saved as ScanResult rows, and
    the parent Scan record is updated on completion.

    Args:
        project_id: ID of the project to scan.
        scan_id: ID of the Scan record tracking this run.
    """
    engine = get_engine()

    # --- Load project and queries ---
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if project is None:
            _fail_scan(engine, scan_id, f"Project {project_id} not found")
            return

        queries = session.exec(
            select(Query).where(Query.project_id == project_id, Query.is_active == True)  # noqa: E712
        ).all()

        if not queries:
            _fail_scan(engine, scan_id, "No active queries for project")
            return

        # Snapshot values needed during scanning (detach from session)
        brand_name = project.brand_name
        brand_aliases = project.brand_aliases
        brand_domain = _extract_brand_domain(project)
        competitors = project.competitors
        query_data = [(q.id, q.text) for q in queries]

    # --- Resolve providers ---
    providers = _get_configured_providers()
    if not providers:
        _fail_scan(engine, scan_id, "No LLM providers configured. Set at least one API key.")
        return

    # Mark scan as running
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is None:
            return
        scan.status = "running"
        scan.providers_used = ",".join(p.name for p in providers)
        scan.total_queries = len(query_data) * len(providers)
        scan.completed_queries = 0
        session.add(scan)
        session.commit()

    # --- Build detector ---
    detector = MentionDetector(brand_name, brand_aliases)

    # --- Scan all (query, provider) pairs ---
    semaphore = asyncio.Semaphore(10)
    completed_count = 0
    completed_lock = asyncio.Lock()

    async def _scan_one(query_id: int, query_text: str, provider: LLMProvider) -> None:
        nonlocal completed_count

        try:
            response = await provider.query(query_text)
        except Exception:
            logger.exception(
                "Provider %s failed for query %s", provider.name, query_id
            )
            # Record a failed result so the scan can continue
            response = None

        if response is not None:
            mention = detector.detect(response.text)
            competitors_found = detector.detect_competitors(response.text, competitors)
            citation = parse_citations(response.text, response.citations, brand_domain)
            brands = extract_brands(
                response.text, brand_name, brand_aliases, mention_result=mention,
            )

            result = ScanResult(
                scan_id=scan_id,
                query_id=query_id,
                provider=provider.name,
                raw_response=response.text,
                brand_mentioned=brands.your_brand_mentioned,
                brand_position=brands.your_brand_position,
                brand_sentiment=brands.your_brand_sentiment,
                brand_context=brands.your_brand_context,
                brand_cited=citation.brand_cited,
                response_tokens=response.tokens_used,
                latency_ms=response.latency_ms,
            )
            result.competitors_mentioned = competitors_found
            result.citations = citation.urls
            result.brands_ranked = [
                {"name": b.name, "position": b.position, "is_your_brand": b.is_your_brand}
                for b in brands.brands
            ]
        else:
            result = ScanResult(
                scan_id=scan_id,
                query_id=query_id,
                provider=provider.name,
                raw_response="",
                brand_mentioned=False,
            )

        # Persist the result
        with Session(engine) as session:
            session.add(result)
            session.commit()

        # Update progress
        async with completed_lock:
            completed_count += 1
            if completed_count % 20 == 0 or completed_count == len(tasks):
                with Session(engine) as session:
                    scan = session.get(Scan, scan_id)
                    if scan is not None:
                        scan.completed_queries = completed_count
                        session.add(scan)
                        session.commit()

    async def _scan_one_throttled(
        query_id: int, query_text: str, provider: LLMProvider
    ) -> None:
        async with semaphore:
            await _scan_one(query_id, query_text, provider)

    tasks = [
        _scan_one_throttled(qid, qtext, provider)
        for qid, qtext in query_data
        for provider in providers
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    # --- Mark scan completed ---
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is not None:
            scan.status = "completed"
            scan.completed_queries = len(tasks)
            scan.completed_at = datetime.now(UTC)
            session.add(scan)
            session.commit()

    logger.info("Scan %s completed: %d results", scan_id, len(tasks))


async def run_single_query_scan(
    project_id: int, query_id: int
) -> list[dict]:
    """Scan a single query across all configured providers.

    Returns a list of result dicts (one per provider) without creating
    a Scan record — intended for quick, ad-hoc testing of individual queries.
    """
    engine = get_engine()

    with Session(engine) as session:
        project = session.get(Project, project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        query = session.get(Query, query_id)
        if query is None:
            raise ValueError(f"Query {query_id} not found")

        brand_name = project.brand_name
        brand_aliases = project.brand_aliases
        brand_domain = _extract_brand_domain(project)
        competitors = project.competitors
        query_text = query.text

    providers = _get_configured_providers()
    if not providers:
        raise ValueError("No LLM providers configured. Set at least one API key.")

    detector = MentionDetector(brand_name, brand_aliases)
    results: list[dict] = []

    async def _scan_provider(provider: LLMProvider) -> dict:
        try:
            response = await provider.query(query_text)
        except Exception:
            logger.exception("Provider %s failed for query %s", provider.name, query_id)
            return {
                "provider": provider.name,
                "raw_response": "",
                "brand_mentioned": False,
                "brand_position": None,
                "brand_sentiment": None,
                "brand_context": None,
                "competitors_mentioned": [],
                "citations": [],
                "brand_cited": False,
                "brands_ranked": [],
                "error": True,
            }

        mention = detector.detect(response.text)
        competitors_found = detector.detect_competitors(response.text, competitors)
        citation = parse_citations(response.text, response.citations, brand_domain)
        brands = extract_brands(
            response.text, brand_name, brand_aliases, mention_result=mention,
        )

        return {
            "provider": provider.name,
            "raw_response": response.text,
            "brand_mentioned": brands.your_brand_mentioned,
            "brand_position": brands.your_brand_position,
            "brand_sentiment": brands.your_brand_sentiment,
            "brand_context": brands.your_brand_context,
            "competitors_mentioned": competitors_found,
            "citations": citation.urls,
            "brand_cited": citation.brand_cited,
            "brands_ranked": [
                {"name": b.name, "position": b.position, "is_your_brand": b.is_your_brand}
                for b in brands.brands
            ],
            "latency_ms": response.latency_ms,
            "error": False,
        }

    tasks = [_scan_provider(p) for p in providers]
    results = await asyncio.gather(*tasks)
    return list(results)


def _fail_scan(engine, scan_id: int, message: str) -> None:
    """Mark a scan as failed with an error message."""
    logger.error("Scan %s failed: %s", scan_id, message)
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is not None:
            scan.status = "failed"
            scan.error_message = message
            scan.completed_at = datetime.now(UTC)
            session.add(scan)
            session.commit()
