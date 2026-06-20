from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# Canonical event types shared by all sources.
ISSUE_DETECTED = "issue.detected"
PARSE_FAILED = "parse.failed"
METRIC_CANDIDATE_DISCOVERED = "metric.candidate.discovered"
METRIC_APPROVED = "metric.approved"
METRIC_RUN_COMPLETED = "metric.run.completed"
GRAPH_MATERIALIZED = "graph.materialized"
FILE_ADDED = "file.added"
FILE_MODIFIED = "file.modified"
FILE_REMOVED = "file.removed"

FILE_EVENTS = {FILE_ADDED, FILE_MODIFIED, FILE_REMOVED}
ALERT_EVENTS = {ISSUE_DETECTED, PARSE_FAILED}
INFO_EVENTS = {METRIC_CANDIDATE_DISCOVERED, METRIC_APPROVED, METRIC_RUN_COMPLETED, GRAPH_MATERIALIZED}


class Event(BaseModel):
    """Normalized event posted to the hub by MetricGraph or ingest_engine."""

    source: str
    event: str
    id: str
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


def make_event_id(*parts: Any) -> str:
    """Deterministic idempotency key from the salient parts of an event."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
