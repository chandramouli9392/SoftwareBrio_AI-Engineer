# Fetchers

DAVE ships with two built-in fetchers and a clear extension point.

| Fetcher | Best for | Notes |
| --- | --- | --- |
| HTTP | Static pages, blogs, docs, landing pages | Fast and cheap |
| Playwright | JavaScript-heavy apps | Requires optional browser install |
| Firecrawl | Managed crawling | Optional integration hook |
| Crawl4AI | Local crawling workflows | Optional integration hook |

Custom fetchers implement `BaseFetcher` and return `FetchResult`.
