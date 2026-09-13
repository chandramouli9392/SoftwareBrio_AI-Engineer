from __future__ import annotations

import pytest

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult
from dave.search import get_search_provider
from dave.search.base import MockSearchProvider, SearchHit
from dave.search.duckduckgo import DuckDuckGoSearchProvider, parse_results


class FakeFetcher(BaseFetcher):
    """Returns canned content and raises for any URL containing 'boom'."""

    async def fetch(self, request: FetchRequest) -> FetchResult:
        if "boom" in request.url:
            raise RuntimeError("synthetic fetch failure")
        return FetchResult(
            url=request.url,
            final_url=request.url,
            status_code=200,
            headers={},
            html="<html><title>Example Domain</title><body>Description: Test page for examples.</body></html>",
            text="<title>Example Domain</title> Description: Test page for examples.",
            elapsed_seconds=0.01,
            fetcher="fake",
        )


def _engine(fetcher: BaseFetcher | None = None) -> DaveEngine:
    config = DaveConfig(
        fetcher="http",
        cache={"enabled": False, "directory": "/tmp/dave-search-test", "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.0,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    return DaveEngine(config=config, fetchers={"http": fetcher or FakeFetcher()})


@pytest.mark.asyncio
async def test_mock_search_provider_returns_limited_hits():
    provider = MockSearchProvider()
    hits = await provider.search("best crm software", limit=3)
    assert len(hits) == 3
    assert all(isinstance(hit, SearchHit) for hit in hits)
    assert all(hit.url.startswith("https://") for hit in hits)
    assert hits[0].rank == 1


@pytest.mark.asyncio
async def test_search_extract_runs_over_all_hits():
    engine = _engine()
    report = await engine.search(
        "best crm software",
        prompt="get the title",
        provider=MockSearchProvider(),
        limit=3,
    )
    assert report.query == "best crm software"
    assert report.provider == "mock"
    assert len(report.items) == 3
    assert all(item.ok for item in report.items)
    assert all(item.data for item in report.items)


@pytest.mark.asyncio
async def test_search_extract_isolates_per_url_failures():
    hits = [
        SearchHit(url="https://good.example/a", title="A", rank=1),
        SearchHit(url="https://boom.example/b", title="B", rank=2),
        SearchHit(url="https://good.example/c", title="C", rank=3),
    ]
    engine = _engine()
    report = await engine.search("anything", prompt="get the title", provider=MockSearchProvider(hits=hits))
    assert [item.ok for item in report.items] == [True, False, True]
    failed = next(item for item in report.items if not item.ok)
    assert failed.error
    assert failed.data is None


@pytest.mark.asyncio
async def test_report_to_dict_is_json_serializable():
    import json

    engine = _engine()
    report = await engine.search("x", prompt="get the title", provider=MockSearchProvider(), limit=2)
    payload = report.to_dict()
    json.dumps(payload)  # must not raise
    assert payload["count"] == 2
    assert payload["results"][0]["ok"] is True


def test_duckduckgo_parser_decodes_redirect_links():
    html = """
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.linear.app%2Fpricing&rut=abc">
        Linear Pricing
      </a>
      <a class="result__snippet">Plans and pricing for Linear.</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://stripe.com">Stripe</a>
    </div>
    """
    hits = parse_results(html, limit=5)
    assert len(hits) == 2
    assert hits[0].url == "https://www.linear.app/pricing"
    assert hits[0].title == "Linear Pricing"
    assert hits[1].url == "https://stripe.com"
    assert hits[0].rank == 1


def test_get_search_provider_resolves_builtins():
    assert isinstance(get_search_provider("mock"), MockSearchProvider)
    assert isinstance(get_search_provider("duckduckgo"), DuckDuckGoSearchProvider)
    assert isinstance(get_search_provider("ddg"), DuckDuckGoSearchProvider)


def test_get_search_provider_rejects_unknown():
    with pytest.raises(ValueError):
        get_search_provider("not_a_real_provider")


def test_search_provider_plugin_registration():
    from dave import plugins

    plugins.registry.clear()
    try:
        custom = MockSearchProvider()
        plugins.register_search("intranet", custom)
        assert get_search_provider("intranet") is custom
        assert "intranet" in plugins.get_search_providers()
    finally:
        plugins.registry.clear()


@pytest.mark.asyncio
async def test_top_level_search_extract_helper():
    import dave

    config = DaveConfig(
        fetcher="http",
        cache={"enabled": False, "directory": "/tmp/dave-search-test", "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.0,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    engine = DaveEngine(config=config, fetchers={"http": FakeFetcher()})
    # exercise the engine method through a directly constructed engine to keep the test offline
    report = await engine.search("crm", prompt="get the title", provider="mock", limit=2)
    assert len(report.items) == 2
    assert hasattr(dave, "search_extract")
