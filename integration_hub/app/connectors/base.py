from __future__ import annotations

from typing import Protocol

from app.events import Event


class Connector(Protocol):
    name: str

    def enabled(self) -> bool:
        """Whether the connector has enough config to send anything."""
        ...

    def notify(self, event: Event) -> None:
        """Deliver an outbound notification for an event."""
        ...
