"""Website content extraction using httpx + BeautifulSoup."""

import structlog
from bs4 import BeautifulSoup, Tag
from httpx import AsyncClient

logger = structlog.get_logger()


async def fetch_page(url: str, timeout: float = 15.0) -> str:
    """Fetch a URL and return the HTML content."""
    async with AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-SEO-Platform/0.1; +https://github.com/ai-seo-platform)"
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def extract_metadata(html: str) -> dict:
    """Extract structured metadata from HTML page.

    Returns:
        Dict with keys: title, meta_description, og_title, og_description,
        h1, h2s, about_link, body_text.
    """
    soup = BeautifulSoup(html, "html.parser")

    meta = {
        "title": "",
        "meta_description": "",
        "og_title": "",
        "og_description": "",
        "og_site_name": "",
        "h1": "",
        "h2s": [],
        "about_link": None,
        "body_text": "",
    }

    # Title
    if soup.title and soup.title.string:
        meta["title"] = soup.title.string.strip()

    # Meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and isinstance(desc_tag, Tag):
        meta["meta_description"] = desc_tag.get("content", "").strip()

    # Open Graph tags
    for og_field in ["og:title", "og:description", "og:site_name"]:
        og_tag = soup.find("meta", attrs={"property": og_field})
        if og_tag and isinstance(og_tag, Tag):
            key = og_field.replace("og:", "og_")
            meta[key] = og_tag.get("content", "").strip()

    # Headings
    h1_tag = soup.find("h1")
    if h1_tag:
        meta["h1"] = h1_tag.get_text(strip=True)

    h2_tags = soup.find_all("h2")
    meta["h2s"] = [h2.get_text(strip=True) for h2 in h2_tags[:10]]

    # Find about page link
    for link in soup.find_all("a", href=True):
        href = link.get("href", "").lower()
        text = link.get_text(strip=True).lower()
        if "about" in href or "about" in text:
            meta["about_link"] = link["href"]
            break

    # Body text (cleaned)
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    body_text = soup.get_text(separator=" ", strip=True)
    # Truncate to avoid excessive token usage
    meta["body_text"] = body_text[:5000]

    return meta


def build_extraction_text(metadata: dict) -> str:
    """Build a clean text representation from extracted metadata for LLM consumption."""
    parts = []
    if metadata["title"]:
        parts.append(f"Title: {metadata['title']}")
    if metadata["og_site_name"]:
        parts.append(f"Site Name: {metadata['og_site_name']}")
    if metadata["meta_description"]:
        parts.append(f"Description: {metadata['meta_description']}")
    if metadata["og_description"] and metadata["og_description"] != metadata["meta_description"]:
        parts.append(f"OG Description: {metadata['og_description']}")
    if metadata["h1"]:
        parts.append(f"Main Heading: {metadata['h1']}")
    if metadata["h2s"]:
        parts.append(f"Sections: {', '.join(metadata['h2s'])}")
    if metadata["body_text"]:
        parts.append(f"\nPage Content:\n{metadata['body_text']}")
    return "\n".join(parts)
