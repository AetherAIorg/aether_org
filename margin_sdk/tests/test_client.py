from __future__ import annotations

import httpx

import margin
from margin.client import Client


def test_configure_sets_bearer_header():
    margin.configure(api_key="mg_test_key", base_url="http://example.com")
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers.get("Authorization"))
        return httpx.Response(200, json={"id": "sess1", "artifacts": [{"id": "a1"}]})

    client = Client()
    auth_header = client._client.headers.get("Authorization")
    client._client = httpx.Client(
        base_url="http://example.com",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": auth_header},
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        fp = Path(tmp) / "demo.sql"
        fp.write_text("SELECT 1")
        client.ingest(fp)
    assert captured[0] == "Bearer mg_test_key"


def test_sync_materialize():
    margin.configure(api_key="mg_test_key", base_url="http://example.com")
    client = Client()
    client._cfg.session_id = "sess1"

    def handler(request: httpx.Request) -> httpx.Response:
        if "materialize" in request.url.path:
            return httpx.Response(200, json={"workspace_id": "w1", "nodes": 2, "edges": 1})
        return httpx.Response(
            200,
            json={"id": "sess1", "parse_job_statuses": [{"id": "j1", "status": "completed"}]},
        )

    client._client = httpx.Client(
        base_url="http://example.com",
        transport=httpx.MockTransport(handler),
    )
    result = client.sync(timeout=2, poll_seconds=0)
    assert result["nodes"] == 2
