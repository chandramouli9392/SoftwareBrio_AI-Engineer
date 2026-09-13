"""Proxy pool management."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProxyStatus:
    """Health state for a proxy."""

    url: str
    failures: int = 0
    disabled: bool = False


class ProxyPool:
    """Round robin proxy manager with basic failure tracking."""

    def __init__(self, proxies: list[str] | None = None, max_failures: int = 3) -> None:
        self._queue: deque[str] = deque(proxies or [])
        self._failures: dict[str, int] = dict.fromkeys(proxies or [], 0)
        self.max_failures = max_failures

    def has_proxies(self) -> bool:
        """Return whether the pool has any active proxies."""
        return bool(self._queue)

    def next(self) -> str | None:
        """Return the next active proxy URL."""
        if not self._queue:
            return None
        proxy = self._queue[0]
        self._queue.rotate(-1)
        return proxy

    def mark_failure(self, proxy: str | None) -> None:
        """Record a proxy failure and remove it when it exceeds max failures."""
        if proxy is None:
            return
        self._failures[proxy] = self._failures.get(proxy, 0) + 1
        if self._failures[proxy] >= self.max_failures:
            self._queue = deque(item for item in self._queue if item != proxy)

    def mark_success(self, proxy: str | None) -> None:
        """Reset failure count after a successful request."""
        if proxy is not None:
            self._failures[proxy] = 0
