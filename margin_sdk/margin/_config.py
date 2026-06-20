from __future__ import annotations

from dataclasses import dataclass, field

_config: "GlobalConfig | None" = None


@dataclass
class GlobalConfig:
    api_key: str
    base_url: str = "http://localhost:8000"
    session_context: dict = field(default_factory=dict)
    declared_links: list[dict] = field(default_factory=list)
    session_id: str | None = None


def configure(*, api_key: str, base_url: str = "http://localhost:8000") -> None:
    global _config
    _config = GlobalConfig(api_key=api_key, base_url=base_url.rstrip("/"))


def get_config() -> GlobalConfig:
    if _config is None:
        raise RuntimeError("Call margin.configure(api_key=..., base_url=...) first")
    return _config
