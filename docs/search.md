# Search and extract

DAVE can find URLs for you. Give it a query, and it searches the web, then runs
the standard extraction pipeline over each result. Search and extraction compose
with no special casing — every production control (cache, retries, rate limits,
confidence, cost tracking) applies to each fetched result.

## CLI

```bash
dave search "best open source CRM" --recipe company_info --limit 5
dave search "linear app pricing" --prompt "get the plans and prices" --output json
```

Options:

| Option | Purpose |
| --- | --- |
| `--recipe`, `-r` | Use a built-in recipe for every result |
| `--prompt`, `-p` | Natural-language extraction prompt for every result |
| `--limit`, `-n` | Number of search results to extract (default 5) |
| `--search-provider` | `duckduckgo` (default), `mock`, or a registered plugin |
| `--provider` / `--model` | LLM provider and model |
| `--fetcher` | `auto`, `http`, `playwright`, or a plugin fetcher |
| `--output`, `-o` | `rich` (default) or `json` |

## Python

```python
import dave

report = await dave.search_extract(
    "best open source CRM",
    prompt="get the company name and pricing",
    limit=5,
)

print(report.query, report.provider, len(report.ok_items))
for item in report.ok_items:
    print(item.hit.rank, item.hit.url, item.data)

# Every result, including failures, with metadata:
for item in report.items:
    if not item.ok:
        print("failed:", item.hit.url, item.error)
```

`search_extract` returns a `SearchReport`:

- `report.items` — every result as a `SearchResultItem` (`hit`, `ok`, `data`, `error`)
- `report.ok_items` — only the successful extractions
- `report.to_dict()` — a JSON-ready dictionary

> The library function is `dave.search_extract` (not `dave.search`) because
> `dave.search` is the provider subpackage. The CLI command is `dave search`.

## Providers

The default provider uses DuckDuckGo's HTML endpoint through the HTTPX and
Beautiful Soup that DAVE already depends on — no API key, no extra dependency,
no LangChain. Select a provider by name:

```python
report = await dave.search_extract("query", provider="duckduckgo")  # default
report = await dave.search_extract("query", provider="mock")        # offline, deterministic
```

Or set `DAVE_SEARCH_PROVIDER` / `DaveConfig.search_provider`.

## Custom providers

Register a provider to search an internal index or a paid search API. Keep the
core lean by shipping any heavy dependency inside your plugin, not the core.

```python
from dave.plugins import register_search
from dave.search.base import BaseSearchProvider, SearchHit

class InternalSearch(BaseSearchProvider):
    name = "internal"

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        # call your search backend, return ranked SearchHits
        return [SearchHit(url="https://intranet.example/doc/1", title="Doc 1", rank=1)]

register_search("internal", InternalSearch())
```

```bash
dave search "quarterly targets" --search-provider internal --recipe company_info
```

## Failure isolation

A result that fails to fetch or extract does not abort the run. It is captured
with `ok=False` and an `error` message, and the rest of the batch continues.
