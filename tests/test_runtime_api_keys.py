"""Tests for request-scoped API key overrides."""

from aiseo.config import (
    get_effective_api_key,
    reset_request_api_key_overrides,
    set_request_api_key_overrides,
)


def test_request_api_key_overrides_take_precedence():
    token = set_request_api_key_overrides({"openai_api_key": "header-key"})
    try:
        assert get_effective_api_key("openai_api_key") == "header-key"
    finally:
        reset_request_api_key_overrides(token)
