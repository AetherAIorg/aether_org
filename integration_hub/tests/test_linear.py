from __future__ import annotations

import hashlib
import hmac

from app.agent.context_agent import ContextAgent
from app.connectors.linear import LinearConnector


def _connector():
    return LinearConnector(
        api_key="", webhook_secret="topsecret", team_id="t", mention_token="@MetricGraph"
    )


def test_parse_metric_prefix():
    c = _connector()
    assert c.parse_query("metric: gross irr") == ("definition", "gross irr")


def test_parse_slash_search():
    c = _connector()
    assert c.parse_query("/metric search net irr") == ("search", "net irr")


def test_parse_slash_definition():
    c = _connector()
    assert c.parse_query("/metric Gross IRR") == ("definition", "Gross IRR")


def test_parse_mention_what_is():
    c = _connector()
    assert c.parse_query("@MetricGraph what is Gross IRR?") == ("definition", "Gross IRR")


def test_parse_mention_bare_term():
    c = _connector()
    assert c.parse_query("@MetricGraph TVPI") == ("definition", "TVPI")


def test_parse_no_trigger_returns_none():
    c = _connector()
    assert c.parse_query("just chatting about the weather") is None


def test_extract_comment_only_on_create():
    c = _connector()
    payload = {
        "type": "Comment",
        "action": "create",
        "data": {
            "id": "c1",
            "body": "metric: irr",
            "issueId": "iss1",
            "parentId": None,
            "userId": "u1",
            "issue": {"id": "iss1", "identifier": "ENG-1"},
        },
    }
    extracted = c.extract_comment(payload)
    assert extracted["comment_id"] == "c1"
    assert extracted["issue_id"] == "iss1"
    assert extracted["author_id"] == "u1"

    payload["action"] = "update"
    assert c.extract_comment(payload) is None


def test_verify_signature():
    c = _connector()
    body = b'{"type":"Comment"}'
    sig = hmac.new(b"topsecret", body, hashlib.sha256).hexdigest()
    assert c.verify_signature(sig, body) is True
    assert c.verify_signature("deadbeef", body) is False


class FakeMG:
    def __init__(self, metric=None, results=None):
        self._metric = metric
        self._results = results or []

    def find_metric_by_name(self, name):
        return self._metric

    def search(self, query):
        return self._results

    def get_graph_context(self, metric_id, depth=2):
        return {"nodes": [], "edges": []}


def test_answer_query_definition_found():
    c = _connector()
    agent = ContextAgent(FakeMG(metric={"canonical_name": "Gross IRR", "status": "approved", "owner": "Ops", "description": "d"}))
    answer = c.answer_query(agent, "definition", "gross irr")
    assert "Gross IRR" in answer
    assert "approved" in answer


def test_answer_query_not_found():
    c = _connector()
    agent = ContextAgent(FakeMG(metric=None))
    answer = c.answer_query(agent, "definition", "nonexistent")
    assert "couldn't find" in answer.lower()
