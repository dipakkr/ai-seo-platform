"""Brand extraction service: URL -> complete brand profile."""

import json
from urllib.parse import urljoin

import structlog

from aiseo.config import get_settings
from aiseo.utils.scraper import build_extraction_text, extract_metadata, fetch_page
from aiseo.utils.text import extract_domain, normalize_url

logger = structlog.get_logger()

EXTRACTION_PROMPT = """\
You are analyzing a SaaS product website. Extract the following as JSON:
{{
  "brand_name": "exact product/company name",
  "brand_aliases": ["common variations, abbreviations, domain name without TLD"],
  "description": "one-paragraph product description",
  "category": "product category (e.g., 'project management', 'email marketing')",
  "competitors": ["up to 5 likely competitors based on category"],
  "features": ["top 5 key features"],
  "target_audience": "primary user persona"
}}

Return ONLY valid JSON, no markdown fences or extra text.

Website content:
<content>{content}</content>
"""


async def extract_brand_profile(url: str) -> dict:
    """Extract a complete brand profile from a URL.

    Args:
        url: The website URL to analyze.

    Returns:
        Dict with brand_name, brand_aliases, description, category,
        competitors, features, target_audience.
    """
    url = normalize_url(url)
    domain = extract_domain(url)
    logger.info("extracting_brand", url=url, domain=domain)

    # Fetch main page
    html = await fetch_page(url)
    metadata = extract_metadata(html)

    # Try to fetch about page if found
    about_text = ""
    if metadata.get("about_link"):
        try:
            about_url = metadata["about_link"]
            if not about_url.startswith("http"):
                about_url = urljoin(url, about_url)
            about_html = await fetch_page(about_url)
            about_meta = extract_metadata(about_html)
            about_text = f"\n\nAbout Page Content:\n{about_meta['body_text']}"
        except Exception:
            logger.debug("about_page_fetch_failed", url=metadata["about_link"])

    content = build_extraction_text(metadata) + about_text
    prompt = EXTRACTION_PROMPT.format(content=content)

    # Use whichever LLM the user has configured
    result = await _call_llm_for_extraction(prompt)

    # Ensure domain alias is present
    parsed = json.loads(result)
    domain_name = domain.split(".")[0]
    aliases = parsed.get("brand_aliases", [])
    if domain_name not in [a.lower() for a in aliases]:
        aliases.append(domain_name)
    if domain not in aliases:
        aliases.append(domain)
    parsed["brand_aliases"] = aliases

    logger.info("brand_extracted", brand=parsed.get("brand_name"), category=parsed.get("category"))
    return parsed


async def _call_llm_for_extraction(prompt: str) -> str:
    """Call the first available LLM for brand extraction.

    Preference order: OpenAI > Anthropic > Gemini.
    """
    settings = get_settings()

    if settings.openai_api_key:
        return await _extract_with_openai(prompt, settings.openai_api_key)
    if settings.anthropic_api_key:
        return await _extract_with_anthropic(prompt, settings.anthropic_api_key)
    if settings.google_api_key:
        return await _extract_with_gemini(prompt, settings.google_api_key)

    raise RuntimeError(
        "No LLM API key configured. Set at least one of: "
        "AISEO_OPENAI_API_KEY, AISEO_ANTHROPIC_API_KEY, AISEO_GOOGLE_API_KEY"
    )


async def _extract_with_openai(prompt: str, api_key: str) -> str:
    """Use OpenAI for brand extraction."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


async def _extract_with_anthropic(prompt: str, api_key: str) -> str:
    """Use Anthropic for brand extraction."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def _extract_with_gemini(prompt: str, api_key: str) -> str:
    """Use Google Gemini for brand extraction."""
    from google import genai

    client = genai.Client(api_key=api_key)
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text
