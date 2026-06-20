from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import Hub, create_app


class FakeMG:
    def __init__(self):
        self.closed = False

    def find_metric_by_name(self, name):
        if "irr" in name.lower():
            return {
                "canonical_name": "Gross IRR",
                "status": "approved",
                "owner": "Ops",
                "domain": "returns",
                "entity": "fund",
                "grain": "fund",
                "description": "Gross internal rate of return.",
                "specs": [],
            }
        return None

    def search(self, query):
        return []

    def close(self):
        self.closed = True


def _build_client(tmp_path, **overrides):
    settings = Settings(
        state_db=str(tmp_path / "hub.db"),
        hub_webhook_secret="hubsecret",
        linear_webhook_secret="lsecret",
        linear_api_key="k",
        linear_bot_user_id="bot",
        hub_config_file="",
        **overrides,
    )
    hub = Hub(settings)
    hub.mg = FakeMG()
    captured = []
    hub.linear.create_comment = lambda issue_id, body, parent_id=None: captured.append((issue_id, body)) or True
    app = create_app(hub=hub)
    return TestClient(app), captured, hub


def test_health(tmp_path):
    client, _, _ = _build_client(tmp_path)
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_webhook_requires_secret(tmp_path):
    client, _, _ = _build_client(tmp_path)
    event = {"source": "ingest", "event": "file.added", "id": "f1", "payload": {"path": "/x.sql"}}
    raw = json.dumps(event)
    # Wrong secret
    resp = client.post("/webhooks/ingest", content=raw, headers={"x-hub-secret": "nope"})
    assert resp.status_code == 401
    # Correct secret
    resp = client.post("/webhooks/ingest", content=raw, headers={"x-hub-secret": "hubsecret"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "dispatched"


def test_linear_webhook_answers_metric_query(tmp_path):
    client, captured, _ = _build_client(tmp_path)
    payload = {
        "type": "Comment",
        "action": "create",
        "data": {
            "id": "c1",
            "body": "metric: gross irr",
            "issueId": "iss1",
            "parentId": None,
            "userId": "u1",
        },
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"lsecret", raw, hashlib.sha256).hexdigest()
    resp = client.post("/webhooks/linear", content=raw, headers={"linear-signature": sig})
    assert resp.status_code == 200
    assert resp.json()["status"] == "answered"
    assert len(captured) == 1
    assert captured[0][0] == "iss1"
    assert "Gross IRR" in captured[0][1]


def test_linear_webhook_ignores_self_author(tmp_path):
    client, captured, _ = _build_client(tmp_path)
    payload = {
        "type": "Comment",
        "action": "create",
        "data": {"id": "c2", "body": "metric: irr", "issueId": "iss1", "userId": "bot"},
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"lsecret", raw, hashlib.sha256).hexdigest()
    resp = client.post("/webhooks/linear", content=raw, headers={"linear-signature": sig})
    assert resp.json()["status"] == "ignored"
    assert len(captured) == 0


def test_linear_webhook_dedupes_comment(tmp_path):
    client, captured, _ = _build_client(tmp_path)
    payload = {
        "type": "Comment",
        "action": "create",
        "data": {"id": "c3", "body": "metric: irr", "issueId": "iss1", "userId": "u1"},
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"lsecret", raw, hashlib.sha256).hexdigest()
    first = client.post("/webhooks/linear", content=raw, headers={"linear-signature": sig})
    second = client.post("/webhooks/linear", content=raw, headers={"linear-signature": sig})
    assert first.json()["status"] == "answered"
    assert second.json()["status"] == "duplicate"
    assert len(captured) == 1
