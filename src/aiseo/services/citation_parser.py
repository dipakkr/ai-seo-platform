"""Extract and deduplicate URLs from LLM responses and provider citations."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class CitationResult:
    """Result of parsing citations from an LLM response."""

    urls: list[str] = field(default_factory=list)
    brand_cited: bool = False


# Regex to find URLs in free text
_URL_PATTERN = re.compile(
    r"https?://[^\s\)\]\},\"'<>]+",
    re.IGNORECASE,
)


def parse_citations(
    response_text: str,
    provider_citations: list[str],
    brand_domain: str,
) -> CitationResult:
    """Extract and deduplicate URLs from response text and provider citations.

    Args:
        response_text: The raw LLM response text.
        provider_citations: URLs already extracted by the provider SDK.
        brand_domain: The brand's domain (e.g. "postzaper.com") to check
            whether the brand itself was cited.

    Returns:
        CitationResult with deduplicated URLs and brand_cited flag.
    """
    urls: list[str] = []

    # 1. Collect provider-supplied citations
    for url in provider_citations:
        url = _clean_url(url)
        if url:
            urls.append(url)

    # 2. Extract URLs from response text
    for match in _URL_PATTERN.finditer(response_text):
        url = _clean_url(match.group(0))
        if url:
            urls.append(url)

    # 3. Deduplicate while preserving order
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        normalized = _normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)

    # 4. Check if brand domain appears in any citation
    brand_domain_lower = brand_domain.lower().strip(".")
    brand_cited = any(_domain_matches(url, brand_domain_lower) for url in unique_urls)

    return CitationResult(urls=unique_urls, brand_cited=brand_cited)


def _clean_url(url: str) -> str:
    """Strip trailing punctuation that isn't part of the URL."""
    url = url.strip()
    # Remove common trailing punctuation picked up by the regex
    while url and url[-1] in (".", ",", ";", ":", ")", "]", "}", "'", '"'):
        url = url[:-1]
    return url


def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication (lowercase host, strip trailing slash)."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.rstrip("/")
    return f"{host}{path}".lower()


def _domain_matches(url: str, brand_domain: str) -> bool:
    """Check if a URL's host matches or is a subdomain of the brand domain."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    # Exact match or subdomain match (e.g. www.postzaper.com matches postzaper.com)
    return host == brand_domain or host.endswith(f".{brand_domain}")
