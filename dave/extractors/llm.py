"""LLM powered extraction with provider adapters."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from dave.core.config import DaveConfig
from dave.core.errors import ExtractionError
from dave.extractors.chunking import chunk_text
from dave.extractors.confidence import ConfidenceReport, score_confidence
from dave.extractors.schema import SchemaAdapter, schema_prompt, validate_against_schema
from dave.monitoring.costs import CostTracker, estimate_tokens

# OpenAI-compatible providers: provider -> (default base url, label, env var fallbacks).
_OPENAI_COMPATIBLE: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "openai": ("https://api.openai.com/v1", "OpenAI", ("DAVE_LLM_API_KEY", "OPENAI_API_KEY")),
    "groq": ("https://api.groq.com/openai/v1", "Groq", ("DAVE_LLM_API_KEY", "GROQ_API_KEY")),
    "mistral": ("https://api.mistral.ai/v1", "Mistral", ("DAVE_LLM_API_KEY", "MISTRAL_API_KEY")),
}

_GEMINI_ENV = ("DAVE_LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


@dataclass(slots=True)
class ExtractionResult:
    """Raw extraction data plus quality metadata."""

    data: dict[str, Any]
    confidence: ConfidenceReport
    evidence: dict[str, str]
    usage: dict[str, int]
    cost_usd: float


class LLMExtractor:
    """Extract JSON from page text using OpenAI, Anthropic, Ollama, or a mock provider."""

    def __init__(self, config: DaveConfig, cost_tracker: CostTracker | None = None) -> None:
        self.config = config
        self.cost_tracker = cost_tracker or CostTracker()

    async def extract(self, text: str, adapter: SchemaAdapter) -> ExtractionResult:
        """Extract and validate structured data from page text."""
        chunks = self._chunk(text)
        merged: dict[str, Any] = {}
        evidence: dict[str, str] = {}
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_cost = 0.0

        for index, chunk in enumerate(chunks):
            raw, usage = await self._call_provider(chunk, adapter, index=index, total=len(chunks))
            parsed = self._parse_json(raw)
            if isinstance(parsed.get("data"), dict):
                data = parsed.get("data", {})
                chunk_evidence = parsed.get("evidence", {})
            else:
                data = dict(parsed)
                chunk_evidence = parsed.get("evidence", {}) if isinstance(parsed.get("evidence"), dict) else {}
                data.pop("evidence", None)
            merged = self._merge(merged, data)
            evidence.update({str(key): str(value) for key, value in chunk_evidence.items()})
            for key in total_usage:
                total_usage[key] += int(usage.get(key, 0))
            total_cost += self.cost_tracker.estimate_cost(self.config.llm.provider, self.config.llm.model, usage)

        validated = validate_against_schema(merged, adapter.model)
        normalized = validated.model_dump() if hasattr(validated, "model_dump") else dict(validated)
        confidence = score_confidence(normalized, text, evidence=evidence)
        return ExtractionResult(
            data=normalized,
            confidence=confidence,
            evidence=evidence,
            usage=total_usage,
            cost_usd=round(total_cost, 6),
        )

    def _chunk(self, text: str) -> list[str]:
        """Split source text into bounded chunks on semantic boundaries."""
        return chunk_text(
            text,
            max_chars=self.config.chunk_size_chars,
            max_chunks=self.config.max_chunks,
            overlap=self.config.chunk_overlap_chars,
        )

    async def _call_provider(self, chunk: str, adapter: SchemaAdapter, *, index: int, total: int) -> tuple[str, dict[str, int]]:
        provider = self.config.llm.provider
        if provider == "mock":
            return self._mock_extract(chunk, adapter), {
                "prompt_tokens": estimate_tokens(chunk) + estimate_tokens(adapter.prompt),
                "completion_tokens": 180,
                "total_tokens": estimate_tokens(chunk) + estimate_tokens(adapter.prompt) + 180,
            }
        if provider in _OPENAI_COMPATIBLE:
            return await self._call_openai_compatible(provider, chunk, adapter, index=index, total=total)
        if provider == "anthropic":
            return await self._call_anthropic(chunk, adapter, index=index, total=total)
        if provider == "gemini":
            return await self._call_gemini(chunk, adapter, index=index, total=total)
        if provider == "ollama":
            return await self._call_ollama(chunk, adapter, index=index, total=total)
        raise ExtractionError(f"Unsupported LLM provider: {provider}")

    def _resolve_api_key(self, env_vars: tuple[str, ...], *, label: str) -> str:
        """Use an explicit config key, then provider-specific environment variables."""
        api_key = self.config.llm.api_key
        if not api_key:
            for name in env_vars:
                value = os.getenv(name)
                if value:
                    api_key = value
                    break
        if not api_key:
            primary = next((name for name in env_vars if name != "DAVE_LLM_API_KEY"), env_vars[0])
            raise ExtractionError(f"{label} provider requires an API key. Set DAVE_LLM_API_KEY or {primary}.")
        return api_key

    def _messages(self, chunk: str, adapter: SchemaAdapter, *, index: int, total: int) -> list[dict[str, str]]:
        """Build provider messages for a chunk."""
        system = (
            "You are DAVE, a production data extraction engine. "
            "Extract only information supported by the source text. "
            "Include an evidence object whose keys match output fields and whose values are short source excerpts."
        )
        user = (
            f"Task: {adapter.prompt}\n"
            f"Chunk {index + 1} of {total}.\n\n"
            f"{schema_prompt(adapter)}\n\n"
            "Source text:\n"
            f"{chunk}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    async def _call_openai_compatible(
        self, provider: str, chunk: str, adapter: SchemaAdapter, *, index: int, total: int
    ) -> tuple[str, dict[str, int]]:
        import asyncio
        import re as _re

        default_base, label, env_vars = _OPENAI_COMPATIBLE[provider]
        api_key = self._resolve_api_key(env_vars, label=label)
        base_url = (self.config.llm.base_url or default_base).rstrip("/")
        model = self.config.llm.model
        # Some models (e.g. openai/gpt-oss-* on Groq) reject response_format json_object.
        _skip_json_format = model.startswith("openai/gpt-oss") or model.startswith("qwen/")
        payload: dict[str, object] = {
            "model": model,
            "messages": self._messages(chunk, adapter, index=index, total=total),
            "temperature": self.config.llm.temperature,
        }
        if not _skip_json_format:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        max_rate_retries = 3
        for attempt in range(max_rate_retries + 1):
            async with httpx.AsyncClient(timeout=self.config.llm.request_timeout_seconds) as client:
                response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            # Handle rate limiting: wait and retry
            if response.status_code == 429 or (
                response.status_code >= 400 and "rate_limit_exceeded" in response.text
            ):
                if attempt < max_rate_retries:
                    # Try to extract retry-after seconds from error message
                    wait_match = _re.search(r"try again in (\d+(?:\.\d+)?)s", response.text)
                    wait_secs = float(wait_match.group(1)) + 1.0 if wait_match else (2 ** attempt) * 5
                    wait_secs = min(wait_secs, 60.0)
                    await asyncio.sleep(wait_secs)
                    continue
                raise ExtractionError(f"{label} extraction failed: {response.text[:500]}")
            # If json_object mode was rejected, retry without it
            if response.status_code >= 400 and "json_validate_failed" in response.text and not _skip_json_format:
                payload.pop("response_format", None)
                async with httpx.AsyncClient(timeout=self.config.llm.request_timeout_seconds) as client:
                    response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            if response.status_code >= 400:
                raise ExtractionError(f"{label} extraction failed: {response.text[:500]}")
            break

        body = response.json()
        usage = body.get("usage", {})
        content = body["choices"][0]["message"]["content"]
        return str(content), {
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }


    async def _call_gemini(self, chunk: str, adapter: SchemaAdapter, *, index: int, total: int) -> tuple[str, dict[str, int]]:
        api_key = self._resolve_api_key(_GEMINI_ENV, label="Gemini")
        messages = self._messages(chunk, adapter, index=index, total=total)
        base_url = (self.config.llm.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        url = f"{base_url}/models/{self.config.llm.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
            "generationConfig": {
                "temperature": self.config.llm.temperature,
                "responseMimeType": "application/json",
            },
        }
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.config.llm.request_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ExtractionError(f"Gemini extraction failed: {response.text[:500]}")
        body = response.json()
        usage = body.get("usageMetadata", {})
        candidates = body.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", [{}]) if candidates else [{}]
        content = "".join(part.get("text", "") for part in parts)
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))
        return content, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": int(usage.get("totalTokenCount", prompt_tokens + completion_tokens)),
        }

    async def _call_anthropic(self, chunk: str, adapter: SchemaAdapter, *, index: int, total: int) -> tuple[str, dict[str, int]]:
        _ANTHROPIC_ENV = ("DAVE_LLM_API_KEY", "ANTHROPIC_API_KEY")
        api_key = self._resolve_api_key(_ANTHROPIC_ENV, label="Anthropic")
        messages = self._messages(chunk, adapter, index=index, total=total)
        payload = {
            "model": self.config.llm.model,
            "max_tokens": 2048,
            "temperature": self.config.llm.temperature,
            "system": messages[0]["content"],
            "messages": [messages[1]],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        base_url = (self.config.llm.base_url or "https://api.anthropic.com/v1").rstrip("/")
        async with httpx.AsyncClient(timeout=self.config.llm.request_timeout_seconds) as client:
            response = await client.post(f"{base_url}/messages", json=payload, headers=headers)
        if response.status_code >= 400:
            raise ExtractionError(f"Anthropic extraction failed: {response.text[:500]}")
        body = response.json()
        usage = body.get("usage", {})
        content = "".join(part.get("text", "") for part in body.get("content", []) if part.get("type") == "text")
        return content, {
            "prompt_tokens": int(usage.get("input_tokens", 0)),
            "completion_tokens": int(usage.get("output_tokens", 0)),
            "total_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
        }

    async def _call_ollama(self, chunk: str, adapter: SchemaAdapter, *, index: int, total: int) -> tuple[str, dict[str, int]]:
        base_url = (self.config.llm.base_url or "http://localhost:11434").rstrip("/")
        prompt = "\n\n".join(message["content"] for message in self._messages(chunk, adapter, index=index, total=total))
        payload = {"model": self.config.llm.model, "prompt": prompt, "stream": False, "format": "json"}
        async with httpx.AsyncClient(timeout=self.config.llm.request_timeout_seconds) as client:
            response = await client.post(f"{base_url}/api/generate", json=payload)
        if response.status_code >= 400:
            raise ExtractionError(f"Ollama extraction failed: {response.text[:500]}")
        body = response.json()
        text = str(body.get("response", "{}"))
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = estimate_tokens(text)
        return text, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _mock_extract(self, chunk: str, adapter: SchemaAdapter) -> str:
        """Return deterministic JSON for tests and credential-free demos."""
        title = self._title(chunk)
        description = self._description(chunk)
        emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", chunk)))
        phones = sorted(set(re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", chunk)))
        links = sorted(set(re.findall(r"https?://[^\s\"'<>]+", chunk)))[:10]

        if adapter.zero_config:
            data: dict[str, Any] = {
                "page_type": self._guess_page_type(chunk),
                "title": title or "Untitled page",
                "summary": description or self._clean(chunk)[:220],
                "key_entities": self._entities(chunk),
                "key_facts": self._sentences(chunk)[:5],
                "links": links,
                "contacts": {"emails": emails, "phones": phones},
                "prices": re.findall(r"[$€£]\s?\d+(?:\.\d{2})?", chunk),
                "products": self._lines_with(chunk, ("product", "platform", "solution", "feature"))[:6],
                "jobs": self._lines_with(chunk, ("engineer", "designer", "manager", "career", "remote"))[:6],
                "calls_to_action": self._lines_with(chunk, ("sign up", "start", "contact", "demo", "buy"))[:6],
            }
        elif adapter.model is not None:
            data = self._mock_model_data(adapter, title, description, emails, phones, links, chunk)
        else:
            data = {"answer": description or title or self._clean(chunk)[:160]}

        return json.dumps({"data": data, "evidence": {key: str(value)[:160] for key, value in data.items()}})

    def _mock_model_data(
        self,
        adapter: SchemaAdapter,
        title: str,
        description: str,
        emails: list[str],
        phones: list[str],
        links: list[str],
        chunk: str,
    ) -> dict[str, Any]:
        properties = adapter.model.model_json_schema().get("properties", {}) if adapter.model is not None else {}
        data: dict[str, Any] = {}
        for field, meta in properties.items():
            lower = field.lower()
            field_type = meta.get("type") or self._type_from_anyof(meta)
            if lower in {"name", "title"}:
                data[field] = title or "Example Domain"
            elif "description" in lower or "summary" in lower:
                data[field] = description or self._clean(chunk)[:160]
            elif "email" in lower:
                data[field] = emails
            elif "phone" in lower:
                data[field] = phones
            elif "social" in lower or "link" in lower or "form" in lower:
                data[field] = links
            elif field_type == "integer":
                data[field] = 0
            elif field_type == "number":
                data[field] = 0.0
            elif field_type == "boolean":
                data[field] = False
            elif field_type == "array":
                data[field] = []
            elif field_type == "object":
                data[field] = {}
            else:
                data[field] = title or description or ""
        return data

    def _type_from_anyof(self, meta: dict[str, Any]) -> str | None:
        for option in meta.get("anyOf", []):
            if isinstance(option, dict) and option.get("type") != "null":
                return str(option.get("type"))
        return None

    def _title(self, chunk: str) -> str:
        title_match = re.search(r"<title>(.*?)</title>", chunk, flags=re.IGNORECASE | re.DOTALL)
        if title_match:
            return self._clean(title_match.group(1))
        heading_match = re.search(r"<h1[^>]*>(.*?)</h1>", chunk, flags=re.IGNORECASE | re.DOTALL)
        return self._clean(heading_match.group(1)) if heading_match else ""

    def _description(self, chunk: str) -> str:
        meta = re.search(r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)[\"']", chunk, flags=re.IGNORECASE)
        if meta:
            return self._clean(meta.group(1))
        description_match = re.search(r"description[:\s]+([^\n.]+)", chunk, flags=re.IGNORECASE)
        if description_match:
            return self._clean(description_match.group(1))
        sentences = self._sentences(chunk)
        return sentences[0] if sentences else ""

    def _guess_page_type(self, chunk: str) -> str:
        lowered = chunk.lower()
        if any(word in lowered for word in ("pricing", "enterprise", "per month", "free trial")):
            return "pricing"
        if any(word in lowered for word in ("careers", "open roles", "job", "remote")):
            return "careers"
        if any(word in lowered for word in ("contact", "email", "phone")):
            return "contact"
        if any(word in lowered for word in ("testimonial", "review", "customer")):
            return "reviews"
        return "company_or_content"

    def _entities(self, chunk: str) -> list[str]:
        words = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,3}\b", self._clean(chunk))
        banned = {"The", "This", "That", "And", "For", "With", "From", "Your"}
        seen: list[str] = []
        for word in words:
            if word not in banned and word not in seen:
                seen.append(word)
        return seen[:10]

    def _lines_with(self, chunk: str, needles: tuple[str, ...]) -> list[str]:
        cleaned = self._clean(chunk)
        lines = [line.strip() for line in re.split(r"[\n|•]", cleaned) if line.strip()]
        return [line[:180] for line in lines if any(needle in line.lower() for needle in needles)]

    def _sentences(self, chunk: str) -> list[str]:
        cleaned = self._clean(chunk)
        return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if 25 <= len(part.strip()) <= 220]

    def _clean(self, value: str) -> str:
        value = re.sub(r"<script.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
        value = re.sub(r"<style.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
        value = re.sub(r"<[^>]+>", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def _parse_json(self, raw: str) -> dict[str, Any]:
        """Parse JSON returned by a provider."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"LLM returned invalid JSON: {raw[:500]}") from exc
        if not isinstance(parsed, dict):
            raise ExtractionError("LLM returned JSON that is not an object")
        return parsed

    def _merge(self, current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Merge chunk data, preferring non-empty later values."""
        merged = dict(current)
        for key, value in update.items():
            if value in (None, "", [], {}) and key in merged:
                continue
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge(merged[key], value)
            else:
                merged[key] = value
        return merged
