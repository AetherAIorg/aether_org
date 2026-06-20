from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ActivityClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def log_query(self, payload: dict[str, Any]) -> None:
        if not self.api_key:
            return
        try:
            self._client.post("/api/v1/activity/queries", json=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to log query activity: %s", exc)

    def close(self) -> None:
        self._client.close()
