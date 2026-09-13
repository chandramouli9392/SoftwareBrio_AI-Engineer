from __future__ import annotations

import base64
import json

import pytest

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.core.errors import ExtractionError
from dave.extractors.schema import make_schema_adapter
from dave.extractors.vision import VisionExtractor

# 1x1 transparent PNG
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _cfg(provider: str, *, api_key: str | None = "k") -> DaveConfig:
    return DaveConfig(
        llm=LLMConfig(provider=provider, model="test-model", api_key=api_key),
        min_confidence=0.0,
    )


def _openai_style(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13}}


@pytest.mark.asyncio
async def test_mock_vision_is_offline_and_deterministic():
    extractor = VisionExtractor(_cfg("mock"))
    adapter = make_schema_adapter("describe the image")
    result = await extractor.extract(PNG_BYTES, adapter)
    assert result.data == {"answer": "mock vision result"}
    assert 0.0 <= result.confidence.overall <= 1.0


@pytest.mark.asyncio
async def test_openai_vision_sends_image_and_parses(httpx_mock):
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        json=_openai_style('{"data": {"title": "Invoice"}}'),
    )
    extractor = VisionExtractor(_cfg("openai"))
    result = await extractor.extract(PNG_BYTES, make_schema_adapter("read it"))
    assert result.data == {"title": "Invoice"}
    body = json.loads(httpx_mock.get_requests()[0].read())
    image_parts = [p for m in body["messages"] for p in (m["content"] if isinstance(m["content"], list) else []) if p.get("type") == "image_url"]
    assert image_parts and image_parts[0]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_anthropic_vision_sends_image_block(httpx_mock):
    httpx_mock.add_response(
        url="https://api.anthropic.com/v1/messages",
        json={"content": [{"type": "text", "text": '{"data": {"total": "$99"}}'}], "usage": {"input_tokens": 8, "output_tokens": 3}},
    )
    extractor = VisionExtractor(_cfg("anthropic"))
    result = await extractor.extract(PNG_BYTES, make_schema_adapter("total?"))
    assert result.data == {"total": "$99"}
    body = json.loads(httpx_mock.get_requests()[0].read())
    blocks = body["messages"][0]["content"]
    assert any(b.get("type") == "image" and b["source"]["data"] for b in blocks)


@pytest.mark.asyncio
async def test_gemini_vision_sends_inline_data(httpx_mock):
    httpx_mock.add_response(
        url="https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent",
        json={"candidates": [{"content": {"parts": [{"text": '{"data": {"label": "cat"}}'}]}}], "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2, "totalTokenCount": 7}},
    )
    extractor = VisionExtractor(_cfg("gemini"))
    result = await extractor.extract(PNG_BYTES, make_schema_adapter("what is it"))
    assert result.data == {"label": "cat"}
    body = json.loads(httpx_mock.get_requests()[0].read())
    parts = body["contents"][0]["parts"]
    assert any("inlineData" in p for p in parts)


@pytest.mark.asyncio
async def test_unsupported_vision_provider_raises():
    extractor = VisionExtractor(_cfg("ollama"))
    with pytest.raises(ExtractionError, match="vision"):
        await extractor.extract(PNG_BYTES, make_schema_adapter("x"))


@pytest.mark.asyncio
async def test_engine_extract_image_from_file(tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(PNG_BYTES)
    engine = DaveEngine(config=_cfg("mock"))
    result = await engine.extract_image(str(img), "describe", include_metadata=True)
    assert result.data == {"answer": "mock vision result"}
    assert result.fetcher == "vision"


@pytest.mark.asyncio
async def test_top_level_extract_image_helper_exists():
    import dave

    assert hasattr(dave, "extract_image")
