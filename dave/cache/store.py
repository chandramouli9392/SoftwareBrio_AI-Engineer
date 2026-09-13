"""SQLite backed cache store."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class CacheStore:
    """Small SQLite cache for fetched pages and extraction payloads."""

    def __init__(self, directory: Path, ttl_seconds: int = 86_400) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "cache.sqlite3"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )

    @staticmethod
    def make_key(*parts: str) -> str:
        """Create a stable hash key from string parts."""
        digest = hashlib.sha256()
        for part in parts:
            digest.update(part.encode("utf-8"))
            digest.update(b"\x00")
        return digest.hexdigest()

    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Return a cached JSON payload when present and not expired."""
        now = time.time()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM cache_entries WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
            if row is None:
                return None
            payload, expires_at = row
            if float(expires_at) < now:
                connection.execute("DELETE FROM cache_entries WHERE namespace = ? AND key = ?", (namespace, key))
                return None
            return json.loads(payload)

    def set(self, namespace: str, key: str, payload: dict[str, Any], ttl_seconds: int | None = None) -> None:
        """Store a JSON payload."""
        now = time.time()
        ttl = ttl_seconds or self.ttl_seconds
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO cache_entries(namespace, key, payload, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (namespace, key, json.dumps(payload, sort_keys=True), now, now + ttl),
            )

    def clear(self) -> None:
        """Delete all cached entries."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM cache_entries")
