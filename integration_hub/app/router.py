from __future__ import annotations

import logging
from typing import Any

from app import formatting
from app.events import (
    Event,
    ALERT_EVENTS,
    FILE_EVENTS,
    INFO_EVENTS,
    ISSUE_DETECTED,
    make_event_id,
)
from app.routing_config import RoutingConfig

logger = logging.getLogger(__name__)


class Router:
    """Fan-out an inbound event to the configured connectors, with dedupe."""

    def __init__(self, slack, teams, linear, state, routing: RoutingConfig) -> None:
        self.slack = slack
        self.teams = teams
        self.linear = linear
        self.state = state
        self.routing = routing

    def dispatch(self, event: Event) -> dict[str, Any]:
        if not self.state.mark_event(event.id):
            logger.info("Duplicate event %s (%s); skipping", event.id, event.event)
            return {"status": "duplicate", "event": event.event}

        targets: list[str] = []

        if self.routing.slack_enabled:
            self.slack.notify(event)
            targets.append("slack")

        if self.routing.teams_enabled and self._teams_wants(event):
            self.teams.notify(event)
            targets.append("teams")

        if (
            self.routing.linear_issues_enabled
            and event.event == ISSUE_DETECTED
            and self._severity(event) >= self.routing.linear_min_severity
        ):
            if self._ensure_linear_issue(event):
                targets.append("linear")

        return {"status": "dispatched", "event": event.event, "targets": targets}

    def _teams_wants(self, event: Event) -> bool:
        if event.event in ALERT_EVENTS:
            return True
        if event.event in FILE_EVENTS:
            return self.routing.teams_file_events
        if event.event in INFO_EVENTS:
            return self.routing.teams_info_events
        return False

    @staticmethod
    def _severity(event: Event) -> int:
        try:
            return int(event.payload.get("severity", 1))
        except (TypeError, ValueError):
            return 1

    def _issue_fingerprint(self, event: Event) -> str:
        p = event.payload
        artifacts = ",".join(sorted(p.get("affected_artifacts", []) or []))
        return make_event_id(p.get("issue_type", ""), p.get("title", ""), artifacts)

    def _ensure_linear_issue(self, event: Event) -> bool:
        fingerprint = self._issue_fingerprint(event)
        existing = self.state.get_linear_issue(fingerprint)
        if existing:
            logger.info("Linear issue already exists for fingerprint %s", fingerprint)
            return False
        title, description = formatting.linear_issue_for_event(event)
        issue = self.linear.create_issue(title, description)
        if issue:
            self.state.set_linear_issue(
                fingerprint, issue.get("id", ""), issue.get("identifier"), issue.get("url")
            )
            logger.info("Created Linear issue %s for %s", issue.get("identifier"), title)
            return True
        return False
