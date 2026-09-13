"""Search provider interface and result types.

A search provider turns a natural-language query into a ranked list of URLs.
DAVE then runs its normal extraction pipeline over those URLs, so search and
extraction compose without any special casing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, is_dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A single search result."""

    url: str
    title: str = ""
    snippet: str = ""
    rank: int = 0


@dataclass(slots=True)
class SearchResultItem:
    """Extraction outcome for one search hit."""

    hit: SearchHit
    ok: bool
    data: Any = None
    error: str | None = None


def _serialize(value: Any) -> Any:
    """Best-effort JSON-friendly serialization for Pydantic models and dataclasses."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return str(value)


@dataclass(slots=True)
class SearchReport:
    """Aggregated search-and-extract results for one query."""

    query: str
    provider: str
    items: list[SearchResultItem]

    @property
    def ok_items(self) -> list[SearchResultItem]:
        """Only the items whose extraction succeeded."""
        return [item for item in self.items if item.ok]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a JSON-ready dictionary."""
        return {
            "query": self.query,
            "provider": self.provider,
            "count": len(self.items),
            "ok_count": len(self.ok_items),
            "results": [
                {
                    "rank": item.hit.rank,
                    "url": item.hit.url,
                    "title": item.hit.title,
                    "snippet": item.hit.snippet,
                    "ok": item.ok,
                    "data": _serialize(item.data) if item.ok else None,
                    "error": item.error,
                }
                for item in self.items
            ],
        }


class BaseSearchProvider(ABC):
    """Abstract search provider."""

    name: str = "base"

    @abstractmethod
    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        """Return up to ``limit`` ranked search hits for ``query``."""


class MockSearchProvider(BaseSearchProvider):
    """Offline, deterministic search provider for tests and credential-free demos."""

    name = "mock"

    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self._hits = hits

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        if self._hits is not None:
            return list(self._hits)[:limit]
        return [
            SearchHit(
                url=f"https://example.com/result-{index}",
                title=f"{query} result {index}",
                snippet=f"Deterministic snippet {index} for {query}.",
                rank=index,
            )
            for index in range(1, limit + 1)
        ]
