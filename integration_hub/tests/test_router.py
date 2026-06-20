from __future__ import annotations

from app.events import Event, ISSUE_DETECTED, FILE_ADDED, make_event_id
from app.router import Router
from app.routing_config import RoutingConfig
from app.state import StateStore


class FakeConnector:
    def __init__(self):
        self.events = []

    def notify(self, event):
        self.events.append(event)


class FakeLinear:
    def __init__(self):
        self.created = []

    def create_issue(self, title, description):
        self.created.append(title)
        return {"id": f"id{len(self.created)}", "identifier": f"ENG-{len(self.created)}", "url": "u"}


def _make_router(tmp_path, routing=None):
    state = StateStore(tmp_path / "state.db")
    slack, teams, linear = FakeConnector(), FakeConnector(), FakeLinear()
    router = Router(slack, teams, linear, state, routing or RoutingConfig())
    return router, slack, teams, linear, state


def _issue_event(event_id="e1"):
    return Event(
        source="metricgraph",
        event=ISSUE_DETECTED,
        id=event_id,
        payload={
            "issue_type": "CONFLICTING_DEFINITION",
            "title": "Gross IRR conflict",
            "severity": 4,
            "affected_artifacts": ["a.sql", "b.dax"],
        },
    )


def test_dispatch_routes_conflict_to_slack_and_linear(tmp_path):
    router, slack, teams, linear, _ = _make_router(tmp_path)
    result = router.dispatch(_issue_event())
    assert result["status"] == "dispatched"
    assert "slack" in result["targets"]
    assert "linear" in result["targets"]
    assert "teams" in result["targets"]  # alerts go to Teams
    assert len(slack.events) == 1
    assert len(linear.created) == 1


def test_duplicate_event_is_skipped(tmp_path):
    router, slack, _, linear, _ = _make_router(tmp_path)
    router.dispatch(_issue_event("dup"))
    result = router.dispatch(_issue_event("dup"))
    assert result["status"] == "duplicate"
    assert len(slack.events) == 1
    assert len(linear.created) == 1


def test_linear_issue_deduped_by_fingerprint(tmp_path):
    router, _, _, linear, _ = _make_router(tmp_path)
    # Same conflict content, different event ids -> only one Linear issue.
    router.dispatch(_issue_event("first"))
    router.dispatch(_issue_event("second"))
    assert len(linear.created) == 1


def test_file_event_skips_teams_and_linear_by_default(tmp_path):
    router, slack, teams, linear, _ = _make_router(tmp_path)
    event = Event(
        source="ingest",
        event=FILE_ADDED,
        id=make_event_id("file", "added", "x.sql"),
        payload={"path": "/x.sql", "content_hash": "abc123"},
    )
    result = router.dispatch(event)
    assert "slack" in result["targets"]
    assert "teams" not in result["targets"]
    assert "linear" not in result["targets"]
    assert len(teams.events) == 0
    assert len(linear.created) == 0


def test_linear_min_severity_gate(tmp_path):
    router, _, _, linear, _ = _make_router(tmp_path, RoutingConfig(linear_min_severity=5))
    router.dispatch(_issue_event())  # severity 4 < 5
    assert len(linear.created) == 0
