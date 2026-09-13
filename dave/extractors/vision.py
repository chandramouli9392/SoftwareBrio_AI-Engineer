"""Vision extraction: structured data from images.

When the DOM lies — canvas-rendered apps, image-only pages, scanned documents,
screenshots — DAVE can extract from the pixels instead. Send an image to a
vision-capable model (OpenAI, Anthropic, or Gemini) and get back the same
validated, confidence-scored structured data the text pipeline produces.

Image extraction has no source text to ground against, so confidence reflects
field completeness and is labelled honestly rather than faked as source overlap.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx

from dave.core.config import DaveConfig
from dave.core.errors import ExtractionError
from dave.extractors.confidence import ConfidenceReport, FieldConfidence
from dave.extractors.llm import ExtractionResult
from dave.extractors.schema import SchemaAdapter, schema_prompt, validate_against_schema
from dave.monitoring.costs import CostTracker, estimate_tokens

_VISION_SYSTEM = (
    "You are DAVE, a production data extraction engine reading an image. "
    "Extract only information visible in the image. Return strict JSON."
)


def _flatten(data: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            items.extend(_flatten(value, name))
        else:
            items.append((name, value))
    return items


def vision_confidence(data: dict[str, Any]) -> ConfidenceReport:
    """Score a vision extraction by field completeness (no source-text grounding)."""
    flattened = _flatten(data)
    if not flattened:
        return ConfidenceReport(overall=0.0, fields=[])
    fields: list[FieldConfidence] = []
    for name, value in flattened:
        filled = value not in (None, "", [], {})
        fields.append(
            FieldConfidence(
                field=name,
                score=0.75 if filled else 0.2,
                reason="vision extraction (completeness, no source-text grounding)",
            )
        )
    overall = round(sum(f.score for f in fields) / len(fields), 3)
    return ConfidenceReport(overall=overall, fields=fields)


def _parse_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Vision model returned invalid JSON: {raw[:500]}") from exc
    if not isinstance(parsed, dict):
        raise ExtractionError("Vision model returned JSON that is not an object")
    return parsed


class VisionExtractor:
    """Extract structured data from an image using a vision-capable LLM."""

    def __init__(self, config: DaveConfig, cost_tracker: CostTracker | None = None) -> None:
        self.config = config
        self.cost_tracker = cost_tracker or CostTracker()

    async def extract(self, image_bytes: bytes, adapter: SchemaAdapter, *, media_type: str = "image/png") -> ExtractionResult:
        """Extract and validate structured data from raw image bytes."""
        provider = self.config.llm.provider
        b64 = base64.b64encode(image_bytes).decode("ascii")
        user_text = f"Task: {adapter.prompt}\n\n{schema_prompt(adapter)}"

        if provider == "mock":
            raw, usage = self._mock(adapter)
        elif provider == "openai":
            raw, usage = await self._openai(user_text, b64, media_type)
        elif provider == "anthropic":
            raw, usage = await self._anthropic(user_text, b64, media_type)
        elif provider == "gemini":
            raw, usage = await self._gemini(user_text, b64, media_type)
        else:
            raise ExtractionError(
                f"Provider {provider!r} does not support vision in DAVE. Use openai, anthropic, or gemini."
            )

        parsed = _parse_json_object(raw)
        data = parsed.get("data") if isinstance(parsed.get("data"), dict) else parsed
        data = {k: v for k, v in data.items() if k != "evidence"}
        validated = validate_against_schema(data, adapter.model)
        normalized = validated.model_dump() if hasattr(validated, "model_dump") else dict(validated)
        cost = self.cost_tracker.estimate_cost(provider, self.config.llm.model, usage)
        return ExtractionResult(
            data=normalized,
            confidence=vision_confidence(normalized),
            evidence=parsed.get("evidence", {}) if isinstance(parsed.get("evidence"), dict) else {},
            usage=usage,
            cost_usd=round(cost, 6),
        )

    def _mock(self, adapter: SchemaAdapter) -> tuple[str, dict[str, int]]:
        if adapter.model is not None:
            properties = adapter.model.model_json_schema().get("properties", {})
            data: dict[str, Any] = dict.fromkeys(properties, "")
        else:
            data = {"answer": "mock vision result"}
        usage = {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}
        return json.dumps({"data": data}), usage

    async def _openai(self, text: str, b64: str, media_type: str) -> tuple[str, dict[str, int]]:
        api_key = self._key(("DAVE_LLM_API_KEY", "OPENAI_API_KEY"), "OpenAI")
        base_url = (self.config.llm.base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": self.config.llm.model,
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                    ],
                },
            ],
            "temperature": self.config.llm.temperature,
            "response_format": {"type": "json_object"},
        }
        body = await self._post(f"{base_url}/chat/completions", payload, {"Authorization": f"Bearer {api_key}"}, "OpenAI")
        usage = body.get("usage", {})
        return str(body["choices"][0]["message"]["content"]), {
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }

    async def _anthropic(self, text: str, b64: str, media_type: str) -> tuple[str, dict[str, int]]:
        api_key = self._key(("DAVE_LLM_API_KEY", "ANTHROPIC_API_KEY"), "Anthropic")
        base_url = (self.config.llm.base_url or "https://api.anthropic.com/v1").rstrip("/")
        payload = {
            "model": self.config.llm.model,
            "max_tokens": 2048,
            "temperature": self.config.llm.temperature,
            "system": _VISION_SYSTEM,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    ],
                }
            ],
        }
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        body = await self._post(f"{base_url}/messages", payload, headers, "Anthropic")
        usage = body.get("usage", {})
        content = "".join(part.get("text", "") for part in body.get("content", []) if part.get("type") == "text")
        return content, {
            "prompt_tokens": int(usage.get("input_tokens", 0)),
            "completion_tokens": int(usage.get("output_tokens", 0)),
            "total_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
        }

    async def _gemini(self, text: str, b64: str, media_type: str) -> tuple[str, dict[str, int]]:
        api_key = self._key(("DAVE_LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"), "Gemini")
        base_url = (self.config.llm.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        url = f"{base_url}/models/{self.config.llm.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": _VISION_SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": text}, {"inlineData": {"mimeType": media_type, "data": b64}}]}],
            "generationConfig": {"temperature": self.config.llm.temperature, "responseMimeType": "application/json"},
        }
        body = await self._post(url, payload, {"x-goog-api-key": api_key}, "Gemini")
        usage = body.get("usageMetadata", {})
        candidates = body.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", [{}]) if candidates else [{}]
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))
        return "".join(part.get("text", "") for part in parts), {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": int(usage.get("totalTokenCount", prompt_tokens + completion_tokens)),
        }

    async def _post(self, url: str, payload: dict[str, Any], headers: dict[str, str], label: str) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", **headers}
        async with httpx.AsyncClient(timeout=self.config.llm.request_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ExtractionError(f"{label} vision extraction failed: {response.text[:500]}")
        return response.json()

    def _key(self, env_vars: tuple[str, ...], label: str) -> str:
        import os

        api_key = self.config.llm.api_key or next((os.getenv(name) for name in env_vars if os.getenv(name)), None)
        if not api_key:
            primary = next((name for name in env_vars if name != "DAVE_LLM_API_KEY"), env_vars[0])
            raise ExtractionError(f"{label} provider requires an API key. Set DAVE_LLM_API_KEY or {primary}.")
        return api_key

    @staticmethod
    def estimate_image_tokens(prompt: str) -> int:
        """Rough prompt-token estimate; image tokens are model-specific."""
        return estimate_tokens(prompt)
