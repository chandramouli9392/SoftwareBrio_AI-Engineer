"""Stealth fetcher for sites that block ordinary automation.

This is an optional plugin fetcher. It runs Playwright with an evasion layer
built from launch flags, a realistic browser context, and an init script that
hides the automation signals most bot walls look for (``navigator.webdriver``,
missing ``window.chrome``, headless WebGL vendor strings, and so on).

It does **not** add a heavy dependency like ``undetected-playwright``. The core
stays lean: the only requirement is Playwright itself, installed through the
``stealth`` extra. Register it with :func:`register_stealth_fetcher` (the CLI
does this automatically for ``--fetcher stealth``).
"""

from __future__ import annotations

import time
from typing import Any

from bs4 import BeautifulSoup

from dave.core.errors import FetchError
from dave.fetchers.base import BaseFetcher, FetcherKind, FetchRequest, FetchResult

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_VIEWPORT = {"width": 1280, "height": 800}

# Injected before any page script runs. Masks the signals bot walls inspect.
STEALTH_INIT_SCRIPT = """
(() => {
  const proto = Object.getPrototypeOf(navigator);
  if (proto && 'webdriver' in proto) { delete proto.webdriver; }
})();
Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => undefined, configurable: true });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
  window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(parameters)
  );
}
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
  if (parameter === 37445) { return 'Intel Inc.'; }
  if (parameter === 37446) { return 'Intel Iris OpenGL Engine'; }
  return getParameter.call(this, parameter);
};
"""


def stealth_launch_args() -> list[str]:
    """Chromium launch flags that remove obvious automation tells."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--start-maximized",
    ]


def stealth_headers(user_agent: str | None = None) -> dict[str, str]:
    """Realistic browser request headers, including client hints."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "Upgrade-Insecure-Requests": "1",
    }
    if user_agent:
        headers["User-Agent"] = user_agent
    return headers


def stealth_context_options(
    user_agent: str | None = None,
    *,
    locale: str = "en-US",
    viewport: dict[str, int] | None = None,
    timezone_id: str = "America/New_York",
) -> dict[str, Any]:
    """Options for ``browser.new_context`` that mimic a real desktop browser."""
    agent = user_agent or DEFAULT_USER_AGENT
    return {
        "user_agent": agent,
        "locale": locale,
        "viewport": dict(viewport or DEFAULT_VIEWPORT),
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
        "timezone_id": timezone_id,
        "extra_http_headers": stealth_headers(agent),
    }


def _load_async_playwright() -> Any:
    """Import Playwright lazily so the core never requires it."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise FetchError(
            "Playwright is not installed. Install the stealth extra with "
            "pip install 'dave-ai[stealth]', then run python -m playwright install chromium."
        ) from exc
    return async_playwright


class StealthFetcher(BaseFetcher):
    """Fetch pages with an anti-detection Playwright configuration."""

    kind = FetcherKind.STEALTH

    def __init__(
        self,
        *,
        headless: bool = True,
        locale: str = "en-US",
        viewport: dict[str, int] | None = None,
        wait_until: str = "networkidle",
    ) -> None:
        self.headless = headless
        self.locale = locale
        self.viewport = viewport
        self.wait_until = wait_until

    async def fetch(self, request: FetchRequest) -> FetchResult:
        """Render a page through a stealth-configured headless browser."""
        async_playwright = _load_async_playwright()

        started = time.perf_counter()
        launch_options: dict[str, Any] = {"headless": self.headless, "args": stealth_launch_args()}
        if request.proxy:
            launch_options["proxy"] = {"server": request.proxy}

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            context = await browser.new_context(
                **stealth_context_options(request.user_agent, locale=self.locale, viewport=self.viewport)
            )
            await context.add_init_script(STEALTH_INIT_SCRIPT)
            page = await context.new_page()
            try:
                response = await page.goto(
                    request.url,
                    wait_until=self.wait_until,
                    timeout=int(request.timeout_seconds * 1000),
                )
                html = await page.content()
                final_url = page.url
                status = response.status if response else 200
                headers = await response.all_headers() if response else {}
            finally:
                await browser.close()

        elapsed = time.perf_counter() - started
        if status >= 400:
            raise FetchError(f"Stealth fetch returned status {status} for {request.url}")
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


def register_stealth_fetcher(name: str = "stealth", **kwargs: Any) -> StealthFetcher:
    """Register a StealthFetcher under ``name`` and return it.

    Example:
        from dave.fetchers.stealth import register_stealth_fetcher
        register_stealth_fetcher()
        result = await dave.extract(url, config=DaveConfig(fetcher="stealth"))
    """
    from dave import plugins

    fetcher = StealthFetcher(**kwargs)
    plugins.register_fetcher(name, fetcher)
    return fetcher
