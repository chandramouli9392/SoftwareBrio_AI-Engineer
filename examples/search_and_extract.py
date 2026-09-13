"""Search the web, then extract structured data from each result.

This runs a live DuckDuckGo search (so it needs network), but uses the mock LLM
so no API key is required:

    python examples/search_and_extract.py

The mock LLM only stands in for extraction. With a real provider key
(OPENAI_API_KEY / ANTHROPIC_API_KEY) swap the config for real structured output.

Some sites block the basic HTTP fetcher with 403s or bot challenges. DAVE
isolates those failures and keeps going, so a partial result set is expected
here. Use --fetcher playwright (or the planned stealth fetcher) for tougher
sites.
"""

from __future__ import annotations

import asyncio

import dave
from dave.core.config import DaveConfig, LLMConfig


async def main() -> None:
    config = DaveConfig(llm=LLMConfig(provider="mock", model="mock"))

    report = await dave.search_extract(
        "best open source CRM",
        prompt="get the product name and a one line summary",
        config=config,
        limit=5,
    )

    print(f"query={report.query!r} provider={report.provider} extracted={len(report.ok_items)}/{len(report.items)}")
    for item in report.items:
        if item.ok:
            print(f"  [{item.hit.rank}] OK   {item.hit.url}")
        else:
            print(f"  [{item.hit.rank}] FAIL {item.hit.url} -> {item.error}")


if __name__ == "__main__":
    asyncio.run(main())
