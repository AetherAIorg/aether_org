from __future__ import annotations

import time
from pathlib import Path

import httpx

from margin._config import get_config
from margin.context import ContextHelper


class Client:
    def __init__(self) -> None:
        cfg = get_config()
        self._cfg = cfg
        self._client = httpx.Client(
            base_url=cfg.base_url,
            timeout=60.0,
            headers={"Authorization": f"Bearer {cfg.api_key}"},
        )
        self.context = ContextHelper(self)

    def declare(self, **kwargs) -> None:
        self._cfg.session_context.update(kwargs)

    def ingest(self, path: str | Path) -> list[str]:
        path = Path(path)
        files_to_upload: list[tuple[str, bytes]] = []
        if path.is_file():
            files_to_upload.append((path.name, path.read_bytes()))
        elif path.is_dir():
            for fp in path.rglob("*"):
                if fp.is_file() and fp.suffix.lower() in {".sql", ".py", ".csv", ".dax", ".xlsx", ".xlsm", ".xls"}:
                    files_to_upload.append((fp.name, fp.read_bytes()))
        else:
            raise FileNotFoundError(path)

        artifact_ids: list[str] = []
        for name, content in files_to_upload:
            data = {}
            if self._cfg.session_context:
                import json

                data["context"] = json.dumps(self._cfg.session_context)
            if self._cfg.session_id:
                data["session_id"] = self._cfg.session_id
            resp = self._client.post(
                "/api/v1/ingest",
                files={"files": (name, content)},
                data=data,
            )
            resp.raise_for_status()
            body = resp.json()
            self._cfg.session_id = body["id"]
            for art in body.get("artifacts") or []:
                artifact_ids.append(art["id"])
        return artifact_ids

    def sync(self, poll_seconds: float = 1.0, timeout: float = 120.0) -> dict:
        if not self._cfg.session_id:
            resp = self._client.post("/api/v1/graph/materialize")
            resp.raise_for_status()
            return resp.json()

        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self._client.get(f"/api/v1/ingest/{self._cfg.session_id}")
            resp.raise_for_status()
            body = resp.json()
            statuses = body.get("parse_job_statuses") or []
            if statuses and all(s.get("status") in {"completed", "failed"} for s in statuses):
                break
            time.sleep(poll_seconds)

        resp = self._client.post("/api/v1/graph/materialize")
        resp.raise_for_status()
        return resp.json()

    class _GraphHelper:
        def __init__(self, client: "Client") -> None:
            self._client = client

        def context(self, metric_name: str) -> dict:
            metric = self._client._find_metric(metric_name)
            if not metric:
                return {"nodes": [], "edges": []}
            resp = self._client._client.get(f"/api/v1/graph/context/{metric['id']}")
            resp.raise_for_status()
            return resp.json()

    @property
    def graph(self) -> _GraphHelper:
        return Client._GraphHelper(self)

    def _find_metric(self, name: str) -> dict | None:
        resp = self._client.get("/api/metrics")
        resp.raise_for_status()
        term = name.strip().lower()
        for m in resp.json():
            if m.get("canonical_name", "").lower() == term:
                return self._client.get(f"/api/metrics/{m['id']}").json()
        return None

    def close(self) -> None:
        self._client.close()
