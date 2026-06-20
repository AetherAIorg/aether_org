from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class StateStore:
    """SQLite-backed dedupe + cross-reference store.

    Tracks three things so the hub stays idempotent under webhook retries:
    - processed inbound event ids (avoid duplicate notifications)
    - issue fingerprint -> Linear issue id (avoid duplicate Linear issues)
    - handled Linear comment ids (avoid duplicate registry replies / loops)
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS linear_issues (
                    fingerprint TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    identifier TEXT,
                    url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS handled_comments (
                    comment_id TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def mark_event(self, event_id: str) -> bool:
        """Return True if this is the first time we've seen event_id."""
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO processed_events (event_id) VALUES (?)", (event_id,)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def get_linear_issue(self, fingerprint: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT issue_id, identifier, url FROM linear_issues WHERE fingerprint = ?",
                (fingerprint,),
            )
            return cur.fetchone()

    def set_linear_issue(
        self, fingerprint: str, issue_id: str, identifier: str | None, url: str | None
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO linear_issues (fingerprint, issue_id, identifier, url) "
                "VALUES (?, ?, ?, ?)",
                (fingerprint, issue_id, identifier, url),
            )

    def mark_comment(self, comment_id: str) -> bool:
        """Return True if this is the first time we've handled comment_id."""
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO handled_comments (comment_id) VALUES (?)", (comment_id,)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def close(self) -> None:
        with self._lock:
            self._conn.close()
