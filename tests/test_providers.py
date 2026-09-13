from __future__ import annotations

import pytest

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.core.errors import ExtractionError
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult


class FakeFetcher(BaseFetcher):
    async def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            url=request.url,
            final_url=request.url,
            status_code=200,
            headers={},
            html="<html><title>Source Page</title></html>",
            text="<title>Source Page</title> some body text",
            elapsed_seconds=0.01,
            fetcher="fake",
        )


def _engine(provider: str, *, api_key: str | None = "test-key") -> DaveEngine:
    config = DaveConfig(
        fetcher="http",
        cache={"enabled": False, "directory": "/tmp/dave-prov", "ttl_seconds": 60},
        llm=LLMConfig(provider=provider, model="test-model", api_key=api_key),
        min_confidence=0.0,
        max_low_confidence_retries=0,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    return DaveEngine(config=config, fetchers={"http": FakeFetcher()})


def _openai_style(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


@pytest.mark.asyncio
async def test_groq_uses_openai_compatible_endpoint(httpx_mock):
    httpx_mock.add_response(
        url="https://api.groq.com/openai/v1/chat/completions",
        json=_openai_style('{"data": {"title": "Groq Title"}, "evidence": {"title": "Source Page"}}'),
    )
    engine = _engine("groq")
    result = await engine.extract("https://example.com", prompt="get the title")
    assert result == {"title": "Groq Title"}


@pytest.mark.asyncio
async def test_mistral_uses_its_endpoint(httpx_mock):
    httpx_mock.add_response(
        url="https://api.mistral.ai/v1/chat/completions",
        json=_openai_style('{"data": {"title": "Mistral Title"}}'),
    )
    engine = _engine("mistral")
    result = await engine.extract("https://example.com", prompt="get the title")
    assert result == {"title": "Mistral Title"}


@pytest.mark.asyncio
async def test_gemini_uses_generative_language_endpoint(httpx_mock):
    httpx_mock.add_response(
        url="https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent",
        json={
            "candidates": [{"content": {"parts": [{"text": '{"data": {"title": "Gemini Title"}}'}]}}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 6, "totalTokenCount": 18},
        },
    )
    engine = _engine("gemini")
    result = await engine.extract("https://example.com", prompt="get the title")
    assert result == {"title": "Gemini Title"}


@pytest.mark.asyncio
async def test_missing_api_key_raises_for_new_provider(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("DAVE_LLM_API_KEY", raising=False)
    engine = _engine("groq", api_key=None)
    with pytest.raises(ExtractionError, match="GROQ_API_KEY|API key"):
        await engine.extract("https://example.com", prompt="get the title")


@pytest.mark.asyncio
async def test_groq_api_key_falls_back_to_env(httpx_mock, monkeypatch):
    monkeypatch.delenv("DAVE_LLM_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    captured = {}

    def match(request):
        captured["auth"] = request.headers.get("Authorization")
        return True

    httpx_mock.add_response(
        url="https://api.groq.com/openai/v1/chat/completions",
        json=_openai_style('{"data": {"ok": true}}'),
        match_headers={},
    )
    engine = _engine("groq", api_key=None)
    await engine.extract("https://example.com", prompt="x")
    requests = httpx_mock.get_requests()
    assert any(r.headers.get("Authorization") == "Bearer env-key" for r in requests)
