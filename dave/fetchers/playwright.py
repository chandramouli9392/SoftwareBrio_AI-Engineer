"""Playwright fetcher for JavaScript rendered pages."""

from __future__ import annotations

import time

from bs4 import BeautifulSoup

from dave.core.errors import FetchError
from dave.fetchers.base import BaseFetcher, FetcherKind, FetchRequest, FetchResult


class PlaywrightFetcher(BaseFetcher):
    """Fetch pages with a headless browser when JavaScript rendering is required."""

    kind = FetcherKind.PLAYWRIGHT

    async def fetch(self, request: FetchRequest) -> FetchResult:
        """Render a page with Playwright and return normalized content."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise FetchError(
                "Playwright is not installed. Install DAVE with the playwright extra, then run playwright install chromium."
            ) from exc

        started = time.perf_counter()
        launch_options: dict[str, object] = {"headless": True}
        if request.proxy:
            launch_options["proxy"] = {"server": request.proxy}

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            context = await browser.new_context(user_agent=request.user_agent)
            page = await context.new_page()
            response = await page.goto(
                request.url,
                wait_until="networkidle",
                timeout=int(request.timeout_seconds * 1000),
            )
            html = await page.content()
            final_url = page.url
            status = response.status if response else 200
            headers = await response.all_headers() if response else {}
            await browser.close()

        elapsed = time.perf_counter() - started
        if status >= 400:
            raise FetchError(f"Playwright fetch returned status {status} for {request.url}")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        return FetchResult(
            url=request.url,
            final_url=final_url,
            status_code=status,
            headers=dict(headers),
            html=html,
            text=text,
            elapsed_seconds=elapsed,
            fetcher=self.kind.value,
        )
