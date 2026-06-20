from __future__ import annotations

from app.query_router import parse_query


def test_context_intent():
    assert parse_query("context: Fund Net IRR") == ("context", "Fund Net IRR")


def test_stewardship_intent():
    assert parse_query("who owns net irr") == ("stewardship", "net irr")


def test_impact_intent():
    assert parse_query("what uses fund_cashflows_v2") == ("impact", "fund_cashflows_v2")
