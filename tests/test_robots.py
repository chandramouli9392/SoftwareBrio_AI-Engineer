from __future__ import annotations

import pytest

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.core.errors import RobotsDisallowedError
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult
from dave.fetchers.robots import RobotsCache, robots_allows

ROBOTS = "User-agent: *\nDisallow: /private\n"


class FakeFetcher(BaseFetcher):
    async def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            url=request.url,
            final_url=request.url,
            status_code=200,
            headers={},
            html="<title>OK</title>",
            text="<title>OK</title> body",
            elapsed_seconds=0.01,
            fetcher="fake",
        )


def test_robots_allows_public_path():
    assert robots_allows(ROBOTS, "https://x.com/public", "dave") is True


def test_robots_blocks_disallowed_path():
    assert robots_allows(ROBOTS, "https://x.com/private/secret", "dave") is False


def test_empty_robots_allows_everything():
    assert robots_allows("", "https://x.com/anything", "dave") is True


@pytest.mark.asyncio
async def test_cache_allows_when_robots_unreachable(monkeypatch):
    cache = RobotsCache()

    async def boom(robots_url: str) -> str:
        raise RuntimeError("network down")

    monkeypatch.setattr(cache, "_fetch_robots", boom)
    assert await cache.allowed("https://x.com/page", "dave") is True


@pytest.mark.asyncio
async def test_cache_blocks_disallowed_and_caches(monkeypatch):
    cache = RobotsCache()
    calls = {"n": 0}

    async def fake(robots_url: str) -> str:
        calls["n"] += 1
        return ROBOTS

    monkeypatch.setattr(cache, "_fetch_robots", fake)
    assert await cache.allowed("https://x.com/private/x", "dave") is False
    assert await cache.allowed("https://x.com/ok", "dave") is True
    assert calls["n"] == 1  # fetched once, cached per domain


@pytest.mark.asyncio
async def test_local_sources_skip_robots():
    cache = RobotsCache()
    assert await cache.allowed("file:///tmp/x.txt", "dave") is True


def _engine(*, respect: bool) -> DaveEngine:
    config = DaveConfig(
        fetcher="http",
        respect_robots_txt=respect,
        cache={"enabled": False, "directory": "/tmp/dave-robots", "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.0,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    return DaveEngine(config=config, fetchers={"http": FakeFetcher()})


@pytest.mark.asyncio
async def test_engine_blocks_when_robots_disallows(monkeypatch):
    engine = _engine(respect=True)

    async def disallow_all(robots_url: str) -> str:
        return "User-agent: *\nDisallow: /\n"

    monkeypatch.setattr(engine.robots, "_fetch_robots", disallow_all)
    with pytest.raises(RobotsDisallowedError):
        await engine.extract("https://blocked.example/page", "get the title")


@pytest.mark.asyncio
async def test_engine_ignores_robots_when_disabled(monkeypatch):
    engine = _engine(respect=False)
    # even a disallow-all robots is ignored because the flag is off (default)
    result = await engine.extract("https://blocked.example/page", "get the title")
    assert result is not None
