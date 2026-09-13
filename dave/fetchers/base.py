"""Fetcher interface and result objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class FetcherKind(str, Enum):
    """Supported fetcher backend identifiers."""

    HTTP = "http"
    PLAYWRIGHT = "playwright"
    STEALTH = "stealth"
    FILE = "file"
    FIRECRAWL = "firecrawl"
    CRAWL4AI = "crawl4ai"


@dataclass(slots=True)
class FetchRequest:
    """A normalized request passed to a fetcher."""

    url: str
    timeout_seconds: float = 30.0
    headers: Mapping[str, str] | None = None
    proxy: str | None = None
    user_agent: str | None = None
    render_js: bool = False


@dataclass(slots=True)
class FetchResult:
    """Fetched page data returned by a fetcher."""

    url: str
    final_url: str
    status_code: int
    headers: Mapping[str, str]
    html: str
    text: str
    elapsed_seconds: float
    fetcher: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        """Serialize this result for cache storage."""
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "headers": dict(self.headers),
            "html": self.html,
            "text": self.text,
            "elapsed_seconds": self.elapsed_seconds,
            "fetcher": self.fetcher,
            "fetched_at": self.fetched_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> FetchResult:
        """Deserialize a fetch result from cache storage."""
        raw_fetched_at = str(data.get("fetched_at"))
        fetched_at = datetime.fromisoformat(raw_fetched_at)
        return cls(
            url=str(data["url"]),
            final_url=str(data["final_url"]),
            status_code=int(data["status_code"]),
            headers=dict(data.get("headers", {})),
            html=str(data.get("html", "")),
            text=str(data.get("text", "")),
            elapsed_seconds=float(data.get("elapsed_seconds", 0.0)),
            fetcher=str(data.get("fetcher", "cache")),
            fetched_at=fetched_at,
        )


class BaseFetcher(ABC):
    """Abstract fetcher implementation."""

    kind: FetcherKind

    @abstractmethod
    async def fetch(self, request: FetchRequest) -> FetchResult:
        """Fetch a page and return normalized content."""
