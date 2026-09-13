# Plugins

DAVE includes a lightweight plugin registry so teams can add custom fetchers, extractors, and recipes without forking the project.

## Register a fetcher

```python
from dave.plugins import register_fetcher
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult

class InternalFetcher(BaseFetcher):
    name = "internal"

    async def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            url=request.url,
            final_url=request.url,
            status_code=200,
            html="<html><title>Internal page</title></html>",
            text="Internal page",
            headers={},
            elapsed_seconds=0.01,
            fetcher=self.name,
        )

register_fetcher("internal", InternalFetcher())
```

After registration, the fetcher can be selected by configuration or used through the engine fetcher map.

## Register a full plugin

```python
from dave import plugins

plugins.register("internal", fetcher=InternalFetcher())
```

The global registry supports fetchers, extractors, and recipes. Registered fetchers are loaded by `DaveEngine` at construction time.

## Plugin ideas

| Plugin type | Examples |
| --- | --- |
| Fetcher | Authenticated browser, Firecrawl adapter, Crawl4AI adapter, enterprise crawler, proxy vendor |
| Extractor | Internal LLM router, deterministic parser, hybrid rules plus LLM extractor |
| Recipe | Market research, real estate listings, app store reviews, docs search, SEC filings |

Plugin contributions are welcome when they include tests, docs, typed interfaces, and clear failure modes.
