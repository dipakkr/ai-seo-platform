"""Fuzzy brand mention detection in LLM responses."""

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process


@dataclass
class MentionResult:
    """Result of detecting brand mentions in text."""

    mentioned: bool = False
    position: int | None = None  # position in a list (1st, 2nd, etc.)
    context: str | None = None  # excerpt around the mention
    sentiment: str = "neutral"  # "positive" | "neutral" | "negative"
    competitors_mentioned: list[str] = field(default_factory=list)


POSITIVE_INDICATORS = [
    "excellent",
    "best",
    "top",
    "great",
    "recommended",
    "popular",
    "leading",
    "powerful",
    "standout",
    "impressive",
    "highly rated",
    "top-rated",
    "well-known",
    "favorite",
    "loved",
]

NEGATIVE_INDICATORS = [
    "poor",
    "worst",
    "avoid",
    "expensive",
    "limited",
    "lacking",
    "outdated",
    "buggy",
    "unreliable",
    "complaints",
    "downsides",
    "drawback",
    "criticism",
    "disappointing",
    "overpriced",
]


class MentionDetector:
    """Detects brand mentions in LLM response text with fuzzy matching."""

    def __init__(self, brand_name: str, brand_aliases: list[str]):
        self.brand_name = brand_name
        self.targets = [brand_name.lower()] + [a.lower() for a in brand_aliases]

    def detect(self, text: str) -> MentionResult:
        """Detect brand mentions in the given text.

        Args:
            text: The LLM response text to analyze.

        Returns:
            MentionResult with mention details.
        """
        text_lower = text.lower()

        # 1. Exact match (case-insensitive)
        mentioned = any(t in text_lower for t in self.targets)

        # 2. Fuzzy match fallback
        if not mentioned:
            words = text_lower.split()
            for target in self.targets:
                if len(target) < 3:
                    continue
                match = process.extractOne(target, words, scorer=fuzz.ratio)
                if match and match[1] >= 85:
                    mentioned = True
                    break

        # 3. Position detection
        position = self._detect_position(text) if mentioned else None

        # 4. Context extraction
        context = self._extract_context(text) if mentioned else None

        # 5. Sentiment analysis
        sentiment = self._basic_sentiment(context) if context else "neutral"

        return MentionResult(
            mentioned=mentioned,
            position=position,
            context=context,
            sentiment=sentiment,
        )

    def detect_competitors(self, text: str, known_competitors: list[str]) -> list[str]:
        """Find which known competitors are mentioned in the text.

        Args:
            text: The LLM response text.
            known_competitors: List of competitor names to look for.

        Returns:
            List of competitor names found in the text.
        """
        text_lower = text.lower()
        found = []
        for comp in known_competitors:
            if comp.lower() in text_lower:
                found.append(comp)
        return found

    def _detect_position(self, text: str) -> int | None:
        """Detect the position of the brand in numbered/bulleted lists."""
        lines = text.split("\n")
        position = 0
        for line in lines:
            stripped = line.strip()
            # Match patterns like "1.", "1)", "#1", "- **Name**"
            if re.match(r"^(\d+[\.\):]|\-|\*|\#\d+)", stripped):
                position += 1
                line_lower = stripped.lower()
                if any(t in line_lower for t in self.targets):
                    return position
        return None

    def _extract_context(self, text: str, window: int = 200) -> str | None:
        """Extract text surrounding the brand mention."""
        text_lower = text.lower()
        for target in self.targets:
            idx = text_lower.find(target)
            if idx != -1:
                start = max(0, idx - window // 2)
                end = min(len(text), idx + len(target) + window // 2)
                return text[start:end].strip()
        return None

    def _basic_sentiment(self, context: str) -> str:
        """Simple keyword-based sentiment of the mention context."""
        if not context:
            return "neutral"
        context_lower = context.lower()
        pos_count = sum(1 for w in POSITIVE_INDICATORS if w in context_lower)
        neg_count = sum(1 for w in NEGATIVE_INDICATORS if w in context_lower)
        if pos_count > neg_count:
            return "positive"
        if neg_count > pos_count:
            return "negative"
        return "neutral"
