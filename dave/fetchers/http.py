"""HTTP fetcher for fast static pages."""

from __future__ import annotations

import time

import httpx
from bs4 import BeautifulSoup

from dave.core.errors import FetchError
from dave.fetchers.base import BaseFetcher, FetcherKind, FetchRequest, FetchResult


class HttpFetcher(BaseFetcher):
    """Fetch pages through plain HTTP using httpx."""

    kind = FetcherKind.HTTP

    async def fetch(self, request: FetchRequest) -> FetchResult:
        """Fetch a URL with an async HTTP client."""
        headers = dict(request.headers or {})
        if request.user_agent:
            headers.setdefault("User-Agent", request.user_agent)
        timeout = httpx.Timeout(request.timeout_seconds)
        proxy = request.proxy
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=headers,
                proxy=proxy,
            ) as client:
                response = await client.get(request.url)
        except httpx.HTTPError as exc:
            raise FetchError(f"HTTP fetch failed for {request.url}: {exc}") from exc

        elapsed = time.perf_counter() - started
        if response.status_code >= 400:
            raise FetchError(f"HTTP fetch returned status {response.status_code} for {request.url}")
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        return FetchResult(
            url=request.url,
            final_url=str(response.url),
            status_code=response.status_code,
            headers=dict(response.headers),
            html=html,
            text=text,
            elapsed_seconds=elapsed,
            fetcher=self.kind.value,
        )
