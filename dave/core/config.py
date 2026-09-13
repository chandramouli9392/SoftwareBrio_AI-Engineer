"""Configuration management for DAVE."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """Configuration for language model providers."""

    provider: Literal["openai", "anthropic", "ollama", "groq", "mistral", "gemini", "mock"] = Field(
        default="openai",
        description="Default LLM provider.",
    )
    model: str = Field(default="gpt-4o-mini", description="Default model name.")
    api_key: str | None = Field(default=None, description="Provider API key.")
    base_url: str | None = Field(default=None, description="Optional provider base URL.")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_retries: int = Field(default=2, ge=0)
    request_timeout_seconds: float = Field(default=45.0, gt=0)


class CacheConfig(BaseModel):
    """Configuration for response and extraction caching."""

    enabled: bool = True
    directory: Path = Field(default_factory=lambda: Path.home() / ".cache" / "dave")
    ttl_seconds: int = Field(default=86_400, ge=1)


class RateLimitConfig(BaseModel):
    """Per domain rate limit configuration."""

    requests_per_minute: int = Field(default=30, ge=1)
    burst: int = Field(default=5, ge=1)


class AntiBotConfig(BaseModel):
    """Controls polite anti-bot hardening for normal scraping workflows."""

    rotate_user_agents: bool = True
    randomize_fingerprint: bool = True
    min_delay_seconds: float = Field(default=0.0, ge=0)
    max_delay_seconds: float = Field(default=1.5, ge=0)
    proxies: list[str] = Field(default_factory=list)

    @field_validator("max_delay_seconds")
    @classmethod
    def max_delay_must_not_be_lower_than_min(cls, value: float, info: object) -> float:
        data = getattr(info, "data", {})
        min_delay = data.get("min_delay_seconds", 0.0)
        if value < min_delay:
            raise ValueError("max_delay_seconds must be greater than or equal to min_delay_seconds")
        return value


def load_dotenv_if_present(env_path: Path | str | None = None) -> None:
    """Load key-value pairs from a local .env file if present without external dependencies."""
    path = Path(env_path) if env_path else Path(".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


class DaveConfig(BaseModel):
    """Top level configuration for the DAVE engine."""

    fetcher: str = Field(
        default="auto",
        description="Fetcher backend: auto, http, playwright, stealth, a known integration, or a registered plugin name.",
    )
    search_provider: str = Field(default="duckduckgo", description="Default web search provider for search-and-extract.")
    timeout_seconds: float = Field(default=30.0, gt=0)
    retries: int = Field(default=2, ge=0)
    min_confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    max_low_confidence_retries: int = Field(default=1, ge=0)
    chunk_size_chars: int = Field(default=12_000, ge=1_000)
    chunk_overlap_chars: int = Field(default=200, ge=0, description="Characters of context repeated across chunk boundaries.")
    max_chunks: int = Field(default=8, ge=1)
    respect_robots_txt: bool = False
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    antibot: AntiBotConfig = Field(default_factory=AntiBotConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> DaveConfig:
        """Create configuration from environment variables."""
        load_dotenv_if_present()
        provider = os.getenv("DAVE_LLM_PROVIDER", "openai")
        default_model = "llama-3.3-70b-versatile" if provider == "groq" else ("gpt-4o-mini" if provider == "openai" else "mock")
        model = os.getenv("DAVE_LLM_MODEL", default_model)
        cache_dir = os.getenv("DAVE_CACHE_DIR")
        api_key = (
            os.getenv("DAVE_LLM_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        return cls(
            llm=LLMConfig(provider=provider, model=model, api_key=api_key),
            cache=CacheConfig(directory=Path(cache_dir)) if cache_dir else CacheConfig(),
            search_provider=os.getenv("DAVE_SEARCH_PROVIDER", "duckduckgo"),
        )
