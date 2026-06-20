from __future__ import annotations

import hashlib
import hmac
import time

from app.connectors.slack import SlackConnector
from app.events import Event, ISSUE_DETECTED
from app import formatting


def test_slack_signature_roundtrip():
    secret = "abc123"
    conn = SlackConnector("", secret, "", "", "")
    body = b"token=x&command=%2Fmetric&text=gross+irr"
    ts = str(int(time.time()))
    basestring = f"v0:{ts}:{body.decode()}"
    digest = hmac.new(secret.encode(), basestring.encode(), hashlib.sha256).hexdigest()
    headers = {"x-slack-request-timestamp": ts, "x-slack-signature": f"v0={digest}"}
    assert conn.verify_signature(headers, body) is True


def test_slack_signature_rejects_tamper():
    conn = SlackConnector("", "abc123", "", "", "")
    ts = str(int(time.time()))
    headers = {"x-slack-request-timestamp": ts, "x-slack-signature": "v0=deadbeef"}
    assert conn.verify_signature(headers, b"body") is False


def test_slack_channel_routing():
    conn = SlackConnector("", "", "C_ALERT", "C_INFO", "C_INGEST")
    event = Event(source="metricgraph", event=ISSUE_DETECTED, id="x", payload={})
    assert conn.channel_for_event(event) == "C_ALERT"


def test_metric_answer_markdown_contains_key_fields():
    metric = {
        "canonical_name": "Net IRR",
        "status": "approved",
        "owner": "Finance",
        "domain": "returns",
        "entity": "fund",
        "grain": "fund",
        "description": "Internal rate of return net of fees.",
        "specs": [{"required_inputs": {"cashflows": "x"}, "transformation_plan": "xirr"}],
    }
    md = formatting.metric_answer_markdown(metric)
    assert "Net IRR" in md
    assert "approved" in md
    assert "net of fees" in md.lower()
    assert "xirr" in md.lower()


def test_event_blocks_have_header_and_summary():
    event = Event(
        source="metricgraph",
        event=ISSUE_DETECTED,
        id="x",
        payload={"title": "Conflict", "issue_type": "CONFLICTING_DEFINITION", "severity": 3, "affected_artifacts": ["a"]},
    )
    blocks = formatting.slack_blocks_for_event(event)
    assert blocks[0]["type"] == "header"
    assert any(b.get("type") == "section" for b in blocks)
