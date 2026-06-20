from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MarginClient:
    """Unified MetricGraph registry + v1 graph client with workspace API key auth."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        resp = self._client.get("/api/search", params={"q": query})
        resp.raise_for_status()
        return resp.json().get("results", [])

    def list_metrics(self) -> list[dict[str, Any]]:
        resp = self._client.get("/api/metrics")
        resp.raise_for_status()
        return resp.json()

    def get_metric(self, metric_id: str) -> dict[str, Any]:
        resp = self._client.get(f"/api/metrics/{metric_id}")
        resp.raise_for_status()
        return resp.json()

    def get_graph_context(self, metric_id: str, depth: int = 2) -> dict[str, Any]:
        resp = self._client.get(f"/api/v1/graph/context/{metric_id}", params={"depth": depth})
        resp.raise_for_status()
        return resp.json()

    def graph_impact(self, ref: str) -> dict[str, Any]:
        resp = self._client.get(f"/api/v1/graph/impact/{ref}")
        resp.raise_for_status()
        return resp.json()

    def find_metric_by_name(self, name: str) -> dict[str, Any] | None:
        term = name.strip().lower()
        if not term:
            return None
        metrics = self.list_metrics()

        for metric in metrics:
            if metric.get("canonical_name", "").lower() == term:
                return self.get_metric(metric["id"])

        partial = [
            m
            for m in metrics
            if term in m.get("canonical_name", "").lower()
            or m.get("canonical_name", "").lower() in term
        ]
        if len(partial) == 1:
            return self.get_metric(partial[0]["id"])
        if len(partial) > 1:
            best = min(partial, key=lambda m: len(m.get("canonical_name", "")))
            return self.get_metric(best["id"])

        try:
            results = self.search(name)
        except httpx.HTTPError:
            results = []
        metric_hits = [r for r in results if r.get("type") == "metric"]
        if metric_hits:
            return self.get_metric(metric_hits[0]["id"])
        return None

    def close(self) -> None:
        self._client.close()
