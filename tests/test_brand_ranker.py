"""Tests for brand ranking extraction."""

from __future__ import annotations

import sys

from aiseo.services.brand_ranker import (
    BrandRanking,
    _extract_ner_brands,
    _parse_list_brands,
    extract_brands,
)
from aiseo.services.mention_detector import MentionResult


def test_parse_list_brands_numbered_and_bulleted():
    text = """
1. **Asana** - project management platform
2. Monday: work OS
- ClickUp (all-in-one app)
""".strip()

    brands = _parse_list_brands(text)
    assert [b.name for b in brands] == ["Asana", "Monday", "ClickUp"]
    assert [b.position for b in brands] == [1, 2, 3]


def test_extract_brands_uses_mention_result_when_brand_not_parsed(monkeypatch):
    monkeypatch.setattr(
        "aiseo.services.brand_ranker._extract_ner_brands",
        lambda _text: [],
    )

    mention = MentionResult(
        mentioned=True,
        position=4,
        context="Acme is a solid option",
        sentiment="positive",
    )

    extracted = extract_brands(
        text="1. Asana\n2. Trello",
        brand_name="Acme",
        brand_aliases=["acme.com"],
        mention_result=mention,
    )

    assert extracted.your_brand_mentioned is True
    assert extracted.your_brand_position == 4
    assert extracted.your_brand_sentiment == "positive"
    assert extracted.your_brand_context == "Acme is a solid option"


def test_extract_brands_merges_list_and_ner(monkeypatch):
    monkeypatch.setattr(
        "aiseo.services.brand_ranker._extract_ner_brands",
        lambda _text: [BrandRanking(name="Notion"), BrandRanking(name="Asana")],
    )

    extracted = extract_brands(
        text="1. Asana\n2. Trello",
        brand_name="Acme",
        brand_aliases=[],
    )

    assert [b.name for b in extracted.brands] == ["Asana", "Trello", "Notion"]


def test_extract_ner_brands_without_spacy_model_returns_empty(monkeypatch):
    class _FakeSpacy:
        @staticmethod
        def load(_name):
            raise OSError("model not installed")

    monkeypatch.setitem(sys.modules, "spacy", _FakeSpacy())
    brands = _extract_ner_brands("Asana and Trello are common picks")
    assert brands == []
