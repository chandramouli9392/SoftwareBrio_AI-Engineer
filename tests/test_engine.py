from __future__ import annotations

import pytest
from pydantic import BaseModel

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult


class TitleSchema(BaseModel):
    title: str
    description: str


class FakeFetcher(BaseFetcher):
    async def fetch(self, request: FetchRequest) -> FetchResult:
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


@pytest.mark.asyncio
async def test_engine_extracts_schema(tmp_path):
    config = DaveConfig(
        fetcher="http",
        cache={"enabled": True, "directory": tmp_path, "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.5,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    engine = DaveEngine(config=config, fetchers={"http": FakeFetcher()})

    result = await engine.extract("https://example.com", TitleSchema)

    assert isinstance(result, TitleSchema)
    assert result.title == "Example Domain"
    assert "Test page" in result.description


def test_diff_detects_changes():
    diff = DaveEngine.diff({"price": "$9", "plan": "Starter"}, {"price": "$19", "plan": "Starter"})
    assert diff == {"price": {"before": "$9", "after": "$19"}}
