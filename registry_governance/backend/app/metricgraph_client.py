from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MetricGraphClient:
    """REST client for MetricGraph registry and discovery APIs."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def list_metrics(self) -> list[dict[str, Any]]:
        resp = self._client.get("/api/metrics")
        resp.raise_for_status()
        return resp.json()

    def get_metric(self, metric_id: str) -> dict[str, Any]:
        resp = self._client.get(f"/api/metrics/{metric_id}")
        resp.raise_for_status()
        return resp.json()

    def list_metric_tags(self, metric_id: str) -> list[dict[str, Any]]:
        resp = self._client.get(f"/api/metrics/{metric_id}/tags")
        resp.raise_for_status()
        return resp.json()

    def list_artifacts(self) -> list[dict[str, Any]]:
        resp = self._client.get("/api/artifacts")
        resp.raise_for_status()
        return resp.json()

    def list_functions(self) -> list[dict[str, Any]]:
        resp = self._client.get("/api/functions")
        resp.raise_for_status()
        return resp.json()

    def list_issues(self, issue_type: str | None = None) -> list[dict[str, Any]]:
        params = {"issue_type": issue_type} if issue_type else None
        resp = self._client.get("/api/issues", params=params)
        resp.raise_for_status()
        return resp.json()

    def list_candidates(self, family: str | None = None) -> list[dict[str, Any]]:
        params = {"family": family} if family else None
        resp = self._client.get("/api/discovery/candidates", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        resp = self._client.get(f"/api/discovery/candidates/{candidate_id}")
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str) -> list[dict[str, Any]]:
        resp = self._client.get("/api/search", params={"q": query})
        resp.raise_for_status()
        return resp.json().get("results", [])

    def close(self) -> None:
        self._client.close()
