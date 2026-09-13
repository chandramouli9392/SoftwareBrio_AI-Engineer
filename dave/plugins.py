"""Community plugin registry for DAVE.

Plugins let developers add custom fetchers, extractors, and recipes without forking the project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from dave.fetchers.base import BaseFetcher


class ExtractorPlugin(Protocol):
    """Protocol for extractor plugins."""

    async def extract(self, text: str, adapter: Any) -> Any:
        """Extract data from text."""


@dataclass(slots=True)
class PluginRegistry:
    """In-memory plugin registry."""

    fetchers: dict[str, BaseFetcher] = field(default_factory=dict)
    extractors: dict[str, ExtractorPlugin] = field(default_factory=dict)
    recipes: dict[str, Any] = field(default_factory=dict)
    search: dict[str, Any] = field(default_factory=dict)

    def register(
        self,
        name: str,
        *,
        fetcher: BaseFetcher | None = None,
        extractor: ExtractorPlugin | None = None,
        recipe: Any | None = None,
        search: Any | None = None,
    ) -> None:
        """Register one or more plugin implementations under a name."""
        if not name or not name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("plugin name must be alphanumeric with optional hyphens or underscores")
        if fetcher is None and extractor is None and recipe is None and search is None:
            raise ValueError("register requires a fetcher, extractor, recipe, or search provider")
        if fetcher is not None:
            self.fetchers[name] = fetcher
        if extractor is not None:
            self.extractors[name] = extractor
        if recipe is not None:
            self.recipes[name] = recipe
        if search is not None:
            self.search[name] = search

    def clear(self) -> None:
        """Clear registered plugins. Mainly useful for tests."""
        self.fetchers.clear()
        self.extractors.clear()
        self.recipes.clear()
        self.search.clear()


registry = PluginRegistry()


def register(
    name: str,
    *,
    fetcher: BaseFetcher | None = None,
    extractor: ExtractorPlugin | None = None,
    recipe: Any | None = None,
    search: Any | None = None,
) -> None:
    """Register a plugin globally.

    Example:
        dave.plugins.register("my_fetcher", fetcher=MyFetcher())
    """
    registry.register(name, fetcher=fetcher, extractor=extractor, recipe=recipe, search=search)


def register_fetcher(name: str, fetcher: BaseFetcher) -> None:
    """Register a custom fetcher globally."""
    register(name, fetcher=fetcher)


def register_search(name: str, provider: Any) -> None:
    """Register a custom search provider globally."""
    register(name, search=provider)


def register_extractor(name: str, extractor: ExtractorPlugin) -> None:
    """Register a custom extractor globally."""
    register(name, extractor=extractor)


def register_recipe(name: str, recipe: Any) -> None:
    """Register a custom recipe globally."""
    register(name, recipe=recipe)


def get_fetchers() -> dict[str, BaseFetcher]:
    """Return registered fetchers."""
    return dict(registry.fetchers)


def get_recipes() -> dict[str, Any]:
    """Return registered recipes."""
    return dict(registry.recipes)


def get_search_providers() -> dict[str, Any]:
    """Return registered search providers."""
    return dict(registry.search)
