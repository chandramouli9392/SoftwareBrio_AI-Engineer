from __future__ import annotations

import pytest

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.core.errors import FetchError
from dave.crawl import extract_links
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult

LINKS_HTML = (
    '<a href="/about">A</a>'
    '<a href="https://other.com/x">ext</a>'
    '<a href="page2.html">p2</a>'
    '<a href="#top">frag</a>'
    '<a href="mailto:a@b.com">mail</a>'
    '<a href="/about">dup</a>'
    '<a href="/doc.pdf">pdf</a>'
)


def test_extract_links_same_domain_relative_and_dedupe():
    links = extract_links(LINKS_HTML, "https://site.com/dir/", same_domain=True)
    assert "https://site.com/about" in links
    assert "https://site.com/dir/page2.html" in links
    assert not any("other.com" in url for url in links)       # external filtered
    assert not any("#" in url or "mailto" in url for url in links)
    assert not any(url.endswith(".pdf") for url in links)     # asset filtered
    assert len(links) == len(set(links))                       # deduped


def test_extract_links_can_allow_external():
    links = extract_links(LINKS_HTML, "https://site.com/", same_domain=False)
    assert any("other.com" in url for url in links)


PAGES = {
    "https://site.com/": "<title>Home</title><a href='/a'>a</a><a href='/b'>b</a>",
    "https://site.com/a": "<title>Alpha</title><a href='/c'>c</a>",
    "https://site.com/b": "<title>Bravo</title>",
    "https://site.com/c": "<title>Charlie</title>",
    "https://site.com/boom": "<title>Boom</title>",
}


class SiteFetcher(BaseFetcher):
    async def fetch(self, request: FetchRequest) -> FetchResult:
        if "boom" in request.url:
            raise RuntimeError("synthetic failure")
        html = PAGES.get(request.url)
        if html is None:
            raise FetchError(f"404 {request.url}")
        return FetchResult(
            url=request.url, final_url=request.url, status_code=200, headers={},
            html=html, text=html.replace("<", " <"), elapsed_seconds=0.01, fetcher="fake",
        )


def _engine(fetcher: BaseFetcher | None = None) -> DaveEngine:
    config = DaveConfig(
        fetcher="http",
        cache={"enabled": False, "directory": "/tmp/dave-crawl", "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.0, max_low_confidence_retries=0, retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    return DaveEngine(config=config, fetchers={"http": fetcher or SiteFetcher()})


@pytest.mark.asyncio
async def test_crawl_visits_linked_pages():
    report = await _engine().crawl("https://site.com/", "get the title", max_pages=10, max_depth=2)
    urls = {item.url for item in report.items}
    assert {"https://site.com/", "https://site.com/a", "https://site.com/b", "https://site.com/c"} <= urls
    assert all(item.ok for item in report.items)
    assert all(item.data for item in report.ok_items)


@pytest.mark.asyncio
async def test_crawl_respects_max_pages():
    report = await _engine().crawl("https://site.com/", "get the title", max_pages=2, max_depth=5)
    assert len(report.items) == 2


@pytest.mark.asyncio
async def test_crawl_respects_max_depth():
    report = await _engine().crawl("https://site.com/", "get the title", max_pages=50, max_depth=1)
    urls = {item.url for item in report.items}
    assert "https://site.com/a" in urls and "https://site.com/b" in urls
    assert "https://site.com/c" not in urls  # depth 2, excluded


@pytest.mark.asyncio
async def test_crawl_does_not_revisit():
    report = await _engine().crawl("https://site.com/", "get the title", max_pages=50, max_depth=3)
    urls = [item.url for item in report.items]
    assert len(urls) == len(set(urls))


@pytest.mark.asyncio
async def test_crawl_isolates_failures():
    pages = {**PAGES, "https://site.com/": "<title>Home</title><a href='/boom'>x</a><a href='/b'>b</a>"}

    class F(SiteFetcher):
        async def fetch(self, request):
            if request.url == "https://site.com/":
                return FetchResult(url=request.url, final_url=request.url, status_code=200, headers={},
                                   html=pages["https://site.com/"], text="home", elapsed_seconds=0.01, fetcher="fake")
            return await super().fetch(request)

    report = await _engine(F()).crawl("https://site.com/", "get the title", max_pages=10, max_depth=2)
    failed = [i for i in report.items if not i.ok]
    assert any("boom" in i.url for i in failed)
    assert any(i.ok for i in report.items)


@pytest.mark.asyncio
async def test_top_level_crawl_helper_exists():
    import dave
    assert hasattr(dave, "crawl")
