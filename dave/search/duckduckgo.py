"""DuckDuckGo HTML search provider.

Uses the dependency-light DuckDuckGo HTML endpoint with httpx and Beautiful
Soup, both already core DAVE dependencies. No API key, no extra packages, no
LangChain. HTML parsing is split into a pure ``parse_results`` function so it
can be tested without network access.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from dave.search.base import BaseSearchProvider, SearchHit

ENDPOINT = "https://html.duckduckgo.com/html/"
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DAVE/0.1; +https://github.com/workwithlos-ui/dave)",
    "Accept": "text/html,application/xhtml+xml",
}


def _clean_url(href: str) -> str:
    """Resolve a DuckDuckGo result href to a direct destination URL."""
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [])
        if target:
            return unquote(target[0])
        return ""
    return href


def parse_results(html: str, *, limit: int = 5) -> list[SearchHit]:
    """Parse DuckDuckGo HTML search results into ranked SearchHits.

    Pure function with no I/O so it is fully unit-testable offline.
    """
    soup = BeautifulSoup(html, "html.parser")
    hits: list[SearchHit] = []
    for anchor in soup.select("a.result__a"):
        url = _clean_url(str(anchor.get("href", "")))
        if not url:
            continue
        title = anchor.get_text(strip=True)
        snippet = ""
        result = anchor.find_parent(class_="result") or anchor.parent
        if result is not None:
            snippet_el = result.select_one(".result__snippet")
            if snippet_el is not None:
                snippet = snippet_el.get_text(strip=True)
        hits.append(SearchHit(url=url, title=title, snippet=snippet, rank=len(hits) + 1))
        if len(hits) >= limit:
            break
    return hits


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """Search the web via DuckDuckGo's HTML endpoint."""

    name = "duckduckgo"

    def __init__(self, config: object | None = None, *, timeout_seconds: float = 15.0) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.post(ENDPOINT, data={"q": query}, headers=_DEFAULT_HEADERS)
        response.raise_for_status()
        return parse_results(response.text, limit=limit)
