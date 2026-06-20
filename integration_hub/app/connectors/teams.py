from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Any

import httpx

from app import formatting
from app.events import Event, ALERT_EVENTS

logger = logging.getLogger(__name__)


class TeamsConnector:
    name = "teams"

    def __init__(self, incoming_webhook_url: str, outgoing_webhook_secret: str) -> None:
        self.incoming_webhook_url = incoming_webhook_url
        self.outgoing_webhook_secret = outgoing_webhook_secret
        self._client = httpx.Client(timeout=15.0)

    def enabled(self) -> bool:
        return bool(self.incoming_webhook_url)

    def notify(self, event: Event) -> None:
        # Keep Teams focused on alerts by default to limit noise.
        if event.event not in ALERT_EVENTS:
            return
        self.post_card(formatting.teams_card_for_event(event))

    def post_card(self, card: dict[str, Any]) -> None:
        if not self.enabled():
            logger.info("Teams disabled (no incoming webhook); would post a card")
            return
        resp = self._client.post(self.incoming_webhook_url, json=card)
        if resp.status_code >= 300:
            logger.warning("Teams webhook failed: %s %s", resp.status_code, resp.text[:200])

    def verify_signature(self, auth_header: str, raw_body: bytes) -> bool:
        """Verify a Teams Outgoing Webhook HMAC.

        Teams signs the request body with the shared secret (base64) and sends
        `Authorization: HMAC <base64-signature>`.
        """
        if not self.outgoing_webhook_secret or not auth_header:
            return False
        try:
            scheme, _, provided = auth_header.partition(" ")
            if scheme.upper() != "HMAC" or not provided:
                return False
            key = base64.b64decode(self.outgoing_webhook_secret)
            digest = hmac.new(key, raw_body, hashlib.sha256).digest()
            expected = base64.b64encode(digest).decode("utf-8")
            return hmac.compare_digest(expected, provided.strip())
        except Exception:
            return False

    def close(self) -> None:
        self._client.close()
