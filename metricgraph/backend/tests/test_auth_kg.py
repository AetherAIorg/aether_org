from __future__ import annotations

import pytest

from app.auth import hash_api_key, generate_api_key, slugify


def test_hash_api_key_deterministic():
    assert hash_api_key("mg_test_abc") == hash_api_key("mg_test_abc")
    assert hash_api_key("mg_test_abc") != hash_api_key("mg_test_xyz")


def test_generate_api_key_prefix():
    live = generate_api_key(test=False)
    test_key = generate_api_key(test=True)
    assert live.startswith("mg_live_")
    assert test_key.startswith("mg_test_")


def test_slugify():
    assert slugify("Investment Ops") == "investment-ops"
