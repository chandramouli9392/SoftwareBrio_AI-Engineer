"""Web search providers for DAVE.

Search turns a query into ranked URLs; DAVE's existing extraction pipeline does
the rest. Providers are pluggable so the core stays dependency-light.
"""

from __future__ import annotations

from dave.search.base import (
    BaseSearchProvider,
    MockSearchProvider,
    SearchHit,
    SearchReport,
    SearchResultItem,
)
from dave.search.duckduckgo import DuckDuckGoSearchProvider

__all__ = [
    "BaseSearchProvider",
    "DuckDuckGoSearchProvider",
    "MockSearchProvider",
    "SearchHit",
    "SearchReport",
    "SearchResultItem",
    "get_search_provider",
]

_BUILTINS = {
    "mock": lambda config: MockSearchProvider(),
    "duckduckgo": lambda config: DuckDuckGoSearchProvider(config),
    "ddg": lambda config: DuckDuckGoSearchProvider(config),
}


def get_search_provider(name: str, *, config: object | None = None) -> BaseSearchProvider:
    """Resolve a search provider by name from built-ins, then registered plugins."""
    key = name.lower()
    if key in _BUILTINS:
        return _BUILTINS[key](config)

    from dave import plugins

    providers = plugins.get_search_providers()
    if key in providers:
        return providers[key]

    known = ", ".join(sorted({"mock", "duckduckgo", *providers}))
    raise ValueError(f"Unknown search provider {name!r}. Available providers: {known}")
