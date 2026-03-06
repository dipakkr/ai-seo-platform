"""Tests for mention detection service."""

from aiseo.services.mention_detector import MentionDetector


class TestMentionDetector:
    def setup_method(self):
        self.detector = MentionDetector(
            brand_name="PostZaper",
            brand_aliases=["postzaper", "postzaper.com", "Post Zaper"],
        )

    def test_exact_match(self):
        text = "I recommend PostZaper for social media scheduling."
        result = self.detector.detect(text)
        assert result.mentioned is True

    def test_case_insensitive_match(self):
        text = "You should try postzaper for automation."
        result = self.detector.detect(text)
        assert result.mentioned is True

    def test_alias_match(self):
        text = "Check out postzaper.com for more details."
        result = self.detector.detect(text)
        assert result.mentioned is True

    def test_no_match(self):
        text = "Buffer and Hootsuite are great tools for scheduling."
        result = self.detector.detect(text)
        assert result.mentioned is False

    def test_position_detection_numbered_list(self):
        text = """Here are the best tools:
1. Buffer - great for scheduling
2. PostZaper - excellent automation
3. Hootsuite - enterprise solution"""
        result = self.detector.detect(text)
        assert result.mentioned is True
        assert result.position == 2

    def test_position_detection_first(self):
        text = """Top picks:
1. PostZaper - the best choice
2. Buffer - runner up"""
        result = self.detector.detect(text)
        assert result.position == 1

    def test_context_extraction(self):
        text = "Among many tools, PostZaper stands out for its automation capabilities."
        result = self.detector.detect(text)
        assert result.context is not None
        assert "PostZaper" in result.context

    def test_positive_sentiment(self):
        text = "PostZaper is an excellent and highly recommended tool for automation."
        result = self.detector.detect(text)
        assert result.sentiment == "positive"

    def test_negative_sentiment(self):
        text = "PostZaper is expensive and has poor customer support, users have many complaints."
        result = self.detector.detect(text)
        assert result.sentiment == "negative"

    def test_neutral_sentiment(self):
        text = "PostZaper is a social media tool that offers scheduling features."
        result = self.detector.detect(text)
        assert result.sentiment == "neutral"

    def test_detect_competitors(self):
        text = "Buffer, Hootsuite, and PostZaper are all options for social media management."
        competitors = self.detector.detect_competitors(
            text, ["Buffer", "Hootsuite", "Later", "Sprout Social"]
        )
        assert "Buffer" in competitors
        assert "Hootsuite" in competitors
        assert "Later" not in competitors

    def test_fuzzy_match_typo(self):
        text = "I've heard PostZapper is decent for scheduling."
        result = self.detector.detect(text)
        # "PostZapper" is close enough to "postzaper" (fuzzy match)
        assert result.mentioned is True
