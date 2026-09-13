"""robots.txt awareness.

Opt-in politeness: when ``DaveConfig.respect_robots_txt`` is enabled, DAVE checks
a site's robots.txt before fetching and refuses disallowed URLs. Results are
cached per domain. If robots.txt is unreachable, DAVE allows the fetch (the
conventional default). Local files are never subject to robots rules.

Uses the standard library ``urllib.robotparser`` for parsing; fetching is async
via httpx so it fits DAVE's pipeline.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


def robots_allows(robots_text: str, url: str, user_agent: str = "*") -> bool:
    """Return whether ``url`` is allowed by the given robots.txt text."""
    if not robots_text.strip():
        return True
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    return parser.can_fetch(user_agent or "*", url)


class RobotsCache:
    """Per-domain robots.txt cache with async fetching."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._cache: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def _fetch_robots(self, robots_url: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.get(robots_url)
        if response.status_code >= 400:
            return ""
        return response.text

    async def allowed(self, url: str, user_agent: str = "*") -> bool:
        """Check robots.txt for ``url``; allow on any fetch/parse failure."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return True
        domain = f"{parsed.scheme}://{parsed.netloc}"
        async with self._lock:
            if domain not in self._cache:
                try:
                    self._cache[domain] = await self._fetch_robots(f"{domain}/robots.txt")
                except Exception:
                    self._cache[domain] = ""
        return robots_allows(self._cache.get(domain, ""), url, user_agent)
