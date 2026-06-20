from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class MarginConfig:
    base_url: str = "http://localhost:8000"
    default_api_key: str = ""
    team_keys: dict[str, str] = field(default_factory=dict)

    def api_key_for_team(self, team_id: str | None) -> str:
        if team_id and team_id in self.team_keys:
            return self.team_keys[team_id]
        return self.default_api_key


@dataclass
class RoutingConfig:
    """Toggles controlling which connectors fire for which event classes.

    Channel IDs / webhook URLs / tokens come from environment settings; this
    file only governs routing behavior so operators can tune noise without
    touching secrets.
    """

    slack_enabled: bool = True
    teams_enabled: bool = True
    linear_issues_enabled: bool = True
    # Mirror file.* and info events to Teams (off by default to limit noise).
    teams_file_events: bool = False
    teams_info_events: bool = False
    # Minimum severity (1-5) for which a Linear issue is created on conflict.
    linear_min_severity: int = 1


def load_routing(path: str | Path | None) -> RoutingConfig:
    if not path:
        return RoutingConfig()
    config_path = Path(path)
    if not config_path.exists():
        return RoutingConfig()
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    routing = raw.get("routing") or {}
    defaults = RoutingConfig()
    return RoutingConfig(
        slack_enabled=bool(routing.get("slack_enabled", defaults.slack_enabled)),
        teams_enabled=bool(routing.get("teams_enabled", defaults.teams_enabled)),
        linear_issues_enabled=bool(
            routing.get("linear_issues_enabled", defaults.linear_issues_enabled)
        ),
        teams_file_events=bool(routing.get("teams_file_events", defaults.teams_file_events)),
        teams_info_events=bool(routing.get("teams_info_events", defaults.teams_info_events)),
        linear_min_severity=int(routing.get("linear_min_severity", defaults.linear_min_severity)),
    )


def load_margin_config(path: str | Path | None) -> MarginConfig:
    if not path:
        return MarginConfig()
    config_path = Path(path)
    if not config_path.exists():
        return MarginConfig()
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    margin = raw.get("margin") or {}
    return MarginConfig(
        base_url=str(margin.get("base_url", "http://localhost:8000")),
        default_api_key=str(margin.get("default_api_key", "")),
        team_keys={str(k): str(v) for k, v in (margin.get("team_keys") or {}).items()},
    )
