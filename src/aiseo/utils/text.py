"""Text processing helpers."""

import re
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """Ensure URL has a scheme and is normalized."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_domain(url: str) -> str:
    """Extract the domain name from a URL."""
    parsed = urlparse(normalize_url(url))
    return parsed.netloc.removeprefix("www.")


def domain_to_brand_hint(url: str) -> str:
    """Derive a rough brand name hint from a domain.

    Example: 'postzaper.com' -> 'PostZaper'
    """
    domain = extract_domain(url)
    name = domain.split(".")[0]
    # Simple title case
    return name.title()


def truncate_text(text: str, max_length: int = 5000) -> str:
    """Truncate text to a maximum length, breaking at word boundary."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:
        return truncated[:last_space] + "..."
    return truncated + "..."


def clean_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into single spaces."""
    return re.sub(r"\s+", " ", text).strip()
