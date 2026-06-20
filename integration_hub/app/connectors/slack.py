from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import httpx

from app import formatting
from app.events import Event, ALERT_EVENTS, FILE_EVENTS, INFO_EVENTS

logger = logging.getLogger(__name__)


class SlackConnector:
    name = "slack"

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        alert_channel: str,
        info_channel: str,
        ingest_channel: str,
    ) -> None:
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.alert_channel = alert_channel
        self.info_channel = info_channel
        self.ingest_channel = ingest_channel
        self._client = httpx.Client(base_url="https://slack.com/api", timeout=15.0)

    def enabled(self) -> bool:
        return bool(self.bot_token)

    def channel_for_event(self, event: Event) -> str | None:
        if event.event in ALERT_EVENTS:
            return self.alert_channel or None
        if event.event in FILE_EVENTS:
            return self.ingest_channel or self.info_channel or None
        if event.event in INFO_EVENTS:
            return self.info_channel or None
        return self.info_channel or None

    def notify(self, event: Event) -> None:
        channel = self.channel_for_event(event)
        if not channel:
            logger.info("Slack: no channel configured for %s; skipping", event.event)
            return
        self.post_message(
            channel,
            text=formatting.event_summary(event),
            blocks=formatting.slack_blocks_for_event(event),
        )

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled():
            logger.info("Slack disabled (no bot token); would post to %s: %s", channel, text)
            return None
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        resp = self._client.post(
            "/chat.postMessage",
            headers={"Authorization": f"Bearer {self.bot_token}"},
            json=payload,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning("Slack postMessage failed: %s", data.get("error"))
        return data

    def verify_signature(self, headers: dict[str, str], raw_body: bytes) -> bool:
        """Verify Slack's v0 request signature.

        See https://api.slack.com/authentication/verifying-requests-from-slack
        """
        if not self.signing_secret:
            return False
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        if not timestamp or not signature:
            return False
        try:
            if abs(time.time() - int(timestamp)) > 60 * 5:
                return False
        except ValueError:
            return False
        basestring = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
        digest = hmac.new(
            self.signing_secret.encode("utf-8"), basestring.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        expected = f"v0={digest}"
        return hmac.compare_digest(expected, signature)

    def close(self) -> None:
        self._client.close()
