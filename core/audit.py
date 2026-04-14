"""
core/audit.py
-------------
SQLite-backed audit log for every tool invocation.

Every tool call is recorded regardless of success or failure. The log is
append-only and stored at the path configured by AUDIT_DB_PATH (default:
./audit.db relative to CWD at startup).

Schema:
    id          INTEGER PRIMARY KEY AUTOINCREMENT
    ts          TEXT    ISO-8601 UTC timestamp
    tool_name   TEXT    name of the called tool
    status      TEXT    "success" | "error"
    duration_ms INTEGER round-trip milliseconds
    api_key_hint TEXT   first 8 chars of the API key (or "anonymous")
    inputs_json TEXT    JSON-serialised inputs (truncated to 4 KB)
    error       TEXT    error message if status == "error", else NULL

Usage:
    from core.audit import audit_log
    audit_log.record(tool_name, status, duration_ms, api_key_hint, inputs, error)
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from core.logger import get_logger

log = get_logger(__name__)

_MAX_INPUT_BYTES = 4096


class AuditLog:
    """Thread-safe SQLite audit logger."""

    def __init__(self, db_path: str = "audit.db") -> None:
        self._path = Path(db_path)
        self._local = threading.local()  # per-thread connection
        self._lock = threading.Lock()
        self._init_schema()

    # ── public API ────────────────────────────────────────────────────────────

    def record(
        self,
        tool_name: str,
        status: str,
        duration_ms: int,
        api_key_hint: str,
        inputs: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """Insert one audit row. Never raises — errors are only logged."""
        try:
            inputs_json = json.dumps(inputs, default=str)
            if len(inputs_json) > _MAX_INPUT_BYTES:
                inputs_json = inputs_json[:_MAX_INPUT_BYTES] + "…[truncated]"
            ts = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """
                INSERT INTO audit_log
                    (ts, tool_name, status, duration_ms, api_key_hint, inputs_json, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, tool_name, status, duration_ms, api_key_hint, inputs_json, error),
            )
            self._conn.commit()
        except Exception as exc:  # pylint: disable=broad-except
            log.error("audit_write_failed", error=str(exc))

    def recent(self, limit: int = 100) -> list[dict]:
        """Return the most recent *limit* audit rows as dicts."""
        rows = self._conn.execute(
            """
            SELECT id, ts, tool_name, status, duration_ms, api_key_hint, error
            FROM   audit_log
            ORDER  BY id DESC
            LIMIT  ?
            """,
            (limit,),
        ).fetchall()
        cols = ["id", "ts", "tool_name", "status", "duration_ms", "api_key_hint", "error"]
        return [dict(zip(cols, row)) for row in rows]

    # ── internals ─────────────────────────────────────────────────────────────

    @property
    def _conn(self) -> sqlite3.Connection:
        """Return (or open) a per-thread SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts           TEXT    NOT NULL,
                    tool_name    TEXT    NOT NULL,
                    status       TEXT    NOT NULL,
                    duration_ms  INTEGER NOT NULL,
                    api_key_hint TEXT    NOT NULL,
                    inputs_json  TEXT,
                    error        TEXT
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ts ON audit_log(ts)"
            )
            self._conn.commit()
        log.info("audit_log_initialised", path=str(self._path))


# Singleton — imported by executor and main
audit_log = AuditLog()
