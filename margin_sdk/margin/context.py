from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from margin.client import Client


class ContextHelper:
    def __init__(self, client: "Client") -> None:
        self._client = client

    def link(self, metric: str, **rels) -> None:
        cfg = self._client._cfg
        link = {"metric": metric, **rels}
        cfg.declared_links.append(link)
        import json

        resp = self._client._client.post(
            "/api/v1/context/links",
            json={"session_id": cfg.session_id, "links": [{"metric": metric, **rels}]},
        )
        resp.raise_for_status()
        body = resp.json()
        cfg.session_id = body.get("session_id")
