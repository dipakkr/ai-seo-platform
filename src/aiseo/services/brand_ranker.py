"""Extract all brands ranked in an LLM response."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz


@dataclass
class BrandRanking:
    """A single brand found in an LLM response."""

    name: str
    position: int | None = None  # 1-based list position, None if prose only
    is_your_brand: bool = False


@dataclass
class ResponseBrands:
    """All brands extracted from an LLM response."""

    brands: list[BrandRanking] = field(default_factory=list)
    your_brand_mentioned: bool = False
    your_brand_position: int | None = None
    your_brand_sentiment: str = "neutral"
    your_brand_context: str | None = None


# Regex for numbered/bulleted list items with a leading brand name.
# Matches patterns like:
#   1. **BrandName** - description
#   1. BrandName: description
#   - **BrandName** (description)
#   * BrandName - description
#   1) BrandName ...
_LIST_ITEM_RE = re.compile(
    r"^"
    r"(?:\d+[\.\)\:]|\-|\*)"  # list bullet: "1.", "1)", "-", "*"
    r"\s+"
    r"(?:\*{1,2})?"  # optional markdown bold prefix
    r"\[?"  # optional markdown link bracket
    r"([A-Z][A-Za-z0-9]+"  # brand starts with uppercase
    r"(?:[\s\.\-][A-Za-z0-9]+){0,3})"  # up to 3 extra words
    r"\]?"  # optional closing bracket
    r"(?:\*{1,2})?"  # optional markdown bold suffix
    r"(?:\(.*?\))?"  # optional link url
)


def _parse_list_brands(text: str) -> list[BrandRanking]:
    """Parse numbered/bulleted lists to extract brand names with positions."""
    brands: list[BrandRanking] = []
    seen: set[str] = set()
    position = 0

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Check if line looks like a list item
        if not re.match(r"^(?:\d+[\.\)\:]|\-|\*)\s+", stripped):
            continue

        position += 1
        match = _LIST_ITEM_RE.match(stripped)
        if match:
            name = match.group(1).strip()
            # Skip generic words that aren't brands
            if name.lower() in _SKIP_WORDS:
                continue
            key = name.lower()
            if key not in seen:
                seen.add(key)
                brands.append(BrandRanking(name=name, position=position))

    return brands


def _extract_ner_brands(text: str) -> list[BrandRanking]:
    """Use spaCy NER to extract ORG/PRODUCT entities from prose."""
    try:
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            return []

        doc = nlp(text[:5000])  # limit to avoid slow processing
        brands: list[BrandRanking] = []
        seen: set[str] = set()

        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT"):
                name = ent.text.strip()
                if len(name) < 2 or name.lower() in _SKIP_WORDS:
                    continue
                key = name.lower()
                if key not in seen:
                    seen.add(key)
                    brands.append(BrandRanking(name=name, position=None))

        return brands
    except ImportError:
        return []


_SKIP_WORDS = frozenset({
    "the", "this", "that", "here", "there", "with", "from", "about",
    "some", "other", "best", "top", "most", "free", "open", "source",
    "key", "main", "pros", "cons", "note", "step", "option", "options",
    "features", "pricing", "summary", "conclusion", "overview",
    "however", "additionally", "furthermore", "alternatively",
})


def _check_your_brand(
    brands: list[BrandRanking],
    brand_name: str,
    brand_aliases: list[str],
) -> tuple[bool, int | None]:
    """Check if any extracted brand matches the user's brand."""
    targets = [brand_name.lower()] + [a.lower() for a in brand_aliases]

    for br in brands:
        name_lower = br.name.lower()
        # Exact match
        if name_lower in targets or any(t in name_lower for t in targets):
            br.is_your_brand = True
            return True, br.position
        # Fuzzy match
        for target in targets:
            if len(target) >= 3 and fuzz.ratio(name_lower, target) >= 85:
                br.is_your_brand = True
                return True, br.position

    return False, None


def extract_brands(
    text: str,
    brand_name: str,
    brand_aliases: list[str],
    mention_result=None,
) -> ResponseBrands:
    """Extract all brands from an LLM response.

    Combines list parsing (primary) with spaCy NER (supplement).
    Uses the existing MentionResult if provided for sentiment/context.

    Args:
        text: Raw LLM response text.
        brand_name: The user's brand name.
        brand_aliases: Alternative names for the user's brand.
        mention_result: Optional MentionResult from MentionDetector.

    Returns:
        ResponseBrands with all extracted brands and your-brand info.
    """
    # 1. Parse list brands (primary — free, fast, covers 90%+ of cases)
    list_brands = _parse_list_brands(text)

    # 2. spaCy NER for brands in prose
    ner_brands = _extract_ner_brands(text)

    # 3. Merge: list brands take priority, NER fills gaps
    seen = {b.name.lower() for b in list_brands}
    all_brands = list(list_brands)
    for nb in ner_brands:
        if nb.name.lower() not in seen:
            seen.add(nb.name.lower())
            all_brands.append(nb)

    # 4. Check if user's brand is in the list
    mentioned, position = _check_your_brand(all_brands, brand_name, brand_aliases)

    # If mention_result says brand is mentioned but we didn't find it in our
    # extracted brands, still respect it
    if mention_result and mention_result.mentioned and not mentioned:
        mentioned = True
        position = mention_result.position

    sentiment = "neutral"
    context = None
    if mention_result:
        sentiment = mention_result.sentiment
        context = mention_result.context

    return ResponseBrands(
        brands=all_brands,
        your_brand_mentioned=mentioned,
        your_brand_position=position,
        your_brand_sentiment=sentiment,
        your_brand_context=context,
    )
