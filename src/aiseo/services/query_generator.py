"""Query generator: brand profile -> set of buyer-intent queries."""

import json
from datetime import datetime, timezone

import structlog

from aiseo.config import get_effective_api_key, get_settings

logger = structlog.get_logger()

INTENT_TEMPLATES: dict[str, list[str]] = {
    "discovery": [
        "best {category} tools",
        "best {category} tools {year}",
        "top {category} software",
        "best {category} for {audience}",
        "{category} tools for startups",
        "best free {category} tools",
        "top rated {category} software {year}",
    ],
    "comparison": [
        "{brand} vs {competitor}",
        "{brand} alternatives",
        "{brand} review",
        "is {brand} good",
        "{brand} vs {competitor} which is better",
        "{brand} pros and cons",
        "alternatives to {brand}",
    ],
    "problem": [
        "how to {feature_verb}",
        "best way to {feature_verb}",
        "tools for {feature_noun}",
        "how do I {feature_verb}",
    ],
    "recommendation": [
        "which {category} should I use",
        "what {category} do you recommend",
        "recommend a {category} for {use_case}",
        "what is the best {category}",
        "suggest a good {category} tool",
    ],
}

LLM_QUERY_GENERATION_PROMPT = """\
Given this SaaS product profile, generate {count} additional queries that a potential \
buyer might type into ChatGPT or Perplexity when looking for a solution like this.

Focus on:
- Natural conversational queries (how people actually talk to AI)
- Problem-aware queries (they know the problem, not the solution)
- Comparison queries (evaluating options)
- Use-case specific queries

Product: {profile_json}

Return ONLY a JSON array of objects: [{{"text": "query", "intent_category": "discovery|comparison|problem|recommendation"}}]
No markdown fences or extra text.
"""


def generate_template_queries(brand_profile: dict) -> list[dict]:
    """Generate queries from templates using the brand profile.

    Args:
        brand_profile: Dict with brand_name, category, competitors, features,
                       target_audience.

    Returns:
        List of dicts with 'text' and 'intent_category'.
    """
    brand = brand_profile.get("brand_name", "")
    category = brand_profile.get("category", "")
    competitors = brand_profile.get("competitors", [])
    features = brand_profile.get("features", [])
    audience = brand_profile.get("target_audience", "")
    year = str(datetime.now(timezone.utc).year)

    queries = []
    seen = set()

    def _add(text: str, intent: str):
        normalized = text.lower().strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            queries.append({"text": text.strip(), "intent_category": intent})

    # Discovery queries
    for template in INTENT_TEMPLATES["discovery"]:
        if "{category}" in template and category:
            text = template.format(
                category=category, year=year, audience=audience or "small teams"
            )
            _add(text, "discovery")

    # Comparison queries - generate for each competitor
    for competitor in competitors[:5]:
        for template in INTENT_TEMPLATES["comparison"]:
            if "{competitor}" in template:
                text = template.format(brand=brand, competitor=competitor)
                _add(text, "comparison")
            elif "{brand}" in template:
                text = template.format(brand=brand)
                _add(text, "comparison")

    # If no competitors, still generate brand-specific comparison queries
    if not competitors:
        for template in INTENT_TEMPLATES["comparison"]:
            if "{competitor}" not in template and "{brand}" in template:
                text = template.format(brand=brand)
                _add(text, "comparison")

    # Problem queries - derive from features
    for feature in features[:5]:
        feature_lower = feature.lower()
        for template in INTENT_TEMPLATES["problem"]:
            if "{feature_verb}" in template:
                _add(template.format(feature_verb=feature_lower), "problem")
            elif "{feature_noun}" in template:
                _add(template.format(feature_noun=feature_lower), "problem")

    # Recommendation queries
    for template in INTENT_TEMPLATES["recommendation"]:
        if "{category}" in template and category:
            text = template.format(
                category=category,
                use_case=audience or "my business",
            )
            _add(text, "recommendation")

    return queries


async def generate_llm_queries(brand_profile: dict, count: int = 30) -> list[dict]:
    """Use an LLM to generate additional queries beyond templates.

    Args:
        brand_profile: The brand profile dict.
        count: Number of additional queries to generate.

    Returns:
        List of dicts with 'text' and 'intent_category'.
    """
    settings = get_settings()
    profile_json = json.dumps(brand_profile, indent=2)
    prompt = LLM_QUERY_GENERATION_PROMPT.format(count=count, profile_json=profile_json)

    try:
        result = await _call_llm_for_queries(prompt, settings)
        queries = json.loads(result)
        if isinstance(queries, list):
            return [
                q
                for q in queries
                if isinstance(q, dict) and "text" in q and "intent_category" in q
            ]
    except Exception:
        logger.warning("llm_query_generation_failed", exc_info=True)

    return []


async def generate_all_queries(
    brand_profile: dict, max_queries: int | None = None
) -> list[dict]:
    """Generate both template and LLM queries.

    Args:
        brand_profile: The brand profile dict.
        max_queries: Maximum total queries. Defaults to settings.default_query_count.

    Returns:
        Deduplicated list of query dicts.
    """
    settings = get_settings()
    if max_queries is None:
        max_queries = settings.default_query_count

    # Start with template queries
    template_queries = generate_template_queries(brand_profile)

    # Generate LLM queries to fill remaining slots
    remaining = max(0, max_queries - len(template_queries))
    llm_queries = []
    if remaining > 0:
        llm_queries = await generate_llm_queries(brand_profile, count=remaining)

    # Deduplicate
    seen = {q["text"].lower().strip() for q in template_queries}
    all_queries = list(template_queries)
    for q in llm_queries:
        normalized = q["text"].lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            all_queries.append(q)

    logger.info(
        "queries_generated",
        template_count=len(template_queries),
        llm_count=len(llm_queries),
        total=len(all_queries),
    )
    return all_queries[:max_queries]


async def _call_llm_for_queries(prompt: str, settings) -> str:
    """Call the first available LLM for query generation."""
    openai_key = get_effective_api_key("openai_api_key") or settings.openai_api_key
    anthropic_key = get_effective_api_key("anthropic_api_key") or settings.anthropic_api_key
    google_key = get_effective_api_key("google_api_key") or settings.google_api_key

    if openai_key:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=openai_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    if anthropic_key:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=anthropic_key)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    if google_key:
        from google import genai

        client = genai.Client(api_key=google_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text

    logger.warning("no_llm_configured_for_query_generation")
    return "[]"
