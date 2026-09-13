from __future__ import annotations

import pytest

from dave.core.errors import FetchError
from dave.fetchers.base import FetchRequest
from dave.fetchers.stealth import (
    STEALTH_INIT_SCRIPT,
    StealthFetcher,
    register_stealth_fetcher,
    stealth_context_options,
    stealth_headers,
    stealth_launch_args,
)


def test_init_script_masks_automation_signals():
    assert "webdriver" in STEALTH_INIT_SCRIPT
    assert "navigator" in STEALTH_INIT_SCRIPT
    assert "chrome" in STEALTH_INIT_SCRIPT


def test_launch_args_disable_automation_flag():
    args = stealth_launch_args()
    assert "--disable-blink-features=AutomationControlled" in args


def test_stealth_headers_look_like_a_real_browser():
    headers = stealth_headers("Mozilla/5.0 (Macintosh) Chrome/124")
    assert headers["Accept-Language"].startswith("en")
    assert "sec-ch-ua" in headers
    assert headers["User-Agent"] == "Mozilla/5.0 (Macintosh) Chrome/124"


def test_stealth_context_options_have_browser_shape():
    options = stealth_context_options()
    assert options["user_agent"]
    assert options["locale"]
    assert options["viewport"]["width"] > 0
    assert options["viewport"]["height"] > 0


def test_fetcher_constructs_without_playwright_installed():
    fetcher = StealthFetcher()
    assert fetcher.kind.value == "stealth"


@pytest.mark.asyncio
async def test_fetch_surfaces_loader_error(monkeypatch):
    def boom() -> object:
        raise FetchError("Playwright is not installed. Install the stealth extra.")

    monkeypatch.setattr("dave.fetchers.stealth._load_async_playwright", boom)
    fetcher = StealthFetcher()
    with pytest.raises(FetchError, match="stealth extra"):
        await fetcher.fetch(FetchRequest(url="https://example.com"))


def test_loader_error_message_is_helpful_when_playwright_absent():
    import importlib.util

    if importlib.util.find_spec("playwright") is not None:
        pytest.skip("playwright is installed in this environment")
    from dave.fetchers.stealth import _load_async_playwright

    with pytest.raises(FetchError) as info:
        _load_async_playwright()
    assert "playwright" in str(info.value).lower()


def test_register_stealth_fetcher_exposes_it_as_a_plugin():
    from dave import plugins

    plugins.registry.clear()
    try:
        register_stealth_fetcher()
        fetchers = plugins.get_fetchers()
        assert "stealth" in fetchers
        assert isinstance(fetchers["stealth"], StealthFetcher)
    finally:
        plugins.registry.clear()
