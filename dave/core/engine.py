"""Main extraction engine."""

from __future__ import annotations

import asyncio
import json
import mimetypes
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from dave import plugins
from dave.antibot.proxies import ProxyPool
from dave.antibot.stealth import DelayPolicy, UserAgentRotator, detect_captcha, random_headers
from dave.cache.store import CacheStore
from dave.core.config import DaveConfig
from dave.core.errors import CaptchaDetectedError, FetchError, LowConfidenceError, RobotsDisallowedError
from dave.crawl import CrawlItem, CrawlReport, extract_links
from dave.extractors.llm import ExtractionResult, LLMExtractor
from dave.extractors.schema import make_schema_adapter, schema_prompt
from dave.extractors.vision import VisionExtractor
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult
from dave.fetchers.file import FileFetcher, is_local_source
from dave.fetchers.http import HttpFetcher
from dave.fetchers.playwright import PlaywrightFetcher
from dave.fetchers.robots import RobotsCache
from dave.monitoring.costs import CostTracker, estimate_tokens
from dave.monitoring.logging import get_logger
from dave.search import get_search_provider
from dave.search.base import BaseSearchProvider, SearchReport, SearchResultItem

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class DaveExtraction:
    """Rich extraction response with metadata."""

    data: Any
    confidence: float
    field_confidence: dict[str, float]
    evidence: dict[str, str]
    cost_usd: float
    fetcher: str
    final_url: str


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """A real-time extraction event."""

    type: str
    message: str
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Estimated token and cost budget for one extraction."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    cached_fetch: bool = False


class DomainRateLimiter:
    """In-memory sliding window rate limiter per domain."""

    def __init__(self, requests_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def wait(self, url: str) -> None:
        """Sleep until the domain is below its configured rate."""
        domain = urlparse(url).netloc
        async with self._lock:
            now = time.monotonic()
            events = self._events[domain]
            while events and now - events[0] > 60:
                events.popleft()
            if len(events) >= self.requests_per_minute:
                delay = 60 - (now - events[0])
                await asyncio.sleep(max(0.0, delay))
            events.append(time.monotonic())


class DaveEngine:
    """Coordinates fetching, extraction, validation, caching, plugins, and monitoring."""

    def __init__(
        self,
        config: DaveConfig | None = None,
        fetchers: dict[str, BaseFetcher] | None = None,
        extractor: LLMExtractor | None = None,
    ) -> None:
        self.config = config or DaveConfig.from_env()
        self.logger = get_logger("dave.engine")
        self.cost_tracker = CostTracker()
        self.extractor = extractor or LLMExtractor(self.config, cost_tracker=self.cost_tracker)
        default_fetchers: dict[str, BaseFetcher] = {
            "http": HttpFetcher(),
            "playwright": PlaywrightFetcher(),
            "file": FileFetcher(),
        }
        default_fetchers.update(plugins.get_fetchers())
        if fetchers:
            default_fetchers.update(fetchers)
        self.fetchers = default_fetchers
        self.cache = CacheStore(self.config.cache.directory, self.config.cache.ttl_seconds) if self.config.cache.enabled else None
        self.rate_limiter = DomainRateLimiter(self.config.rate_limit.requests_per_minute)
        self.user_agents = UserAgentRotator()
        self.proxies = ProxyPool(self.config.antibot.proxies)
        self.delay_policy = DelayPolicy(self.config.antibot.min_delay_seconds, self.config.antibot.max_delay_seconds)
        self.robots = RobotsCache()

    async def extract(
        self,
        url: str,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        include_metadata: bool = False,
        force_refresh: bool = False,
    ) -> T | dict[str, Any] | DaveExtraction:
        """Extract structured data from a URL.

        If no prompt or schema is supplied, DAVE runs zero-config extraction and infers useful structure.
        """
        adapter = make_schema_adapter(schema_or_prompt, prompt=prompt)
        fetch_result = await self.fetch(url, force_refresh=force_refresh)
        extraction = await self._extract_with_quality_retry(fetch_result, adapter)
        output = adapter.model.model_validate(extraction.data) if adapter.model else extraction.data
        if include_metadata:
            return DaveExtraction(
                data=output,
                confidence=extraction.confidence.overall,
                field_confidence={field.field: field.score for field in extraction.confidence.fields},
                evidence=extraction.evidence,
                cost_usd=extraction.cost_usd,
                fetcher=fetch_result.fetcher,
                final_url=fetch_result.final_url,
            )
        return output

    def extract_sync(
        self,
        url: str,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        include_metadata: bool = False,
        force_refresh: bool = False,
    ) -> T | dict[str, Any] | DaveExtraction:
        """Run extraction from synchronous code."""
        return asyncio.run(
            self.extract(
                url,
                schema_or_prompt,
                prompt=prompt,
                include_metadata=include_metadata,
                force_refresh=force_refresh,
            )
        )

    async def crawl(
        self,
        start_url: str,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        max_pages: int = 10,
        max_depth: int = 2,
        same_domain: bool = True,
    ) -> CrawlReport:
        """Crawl a site breadth-first and extract from each page.

        Bounded by ``max_pages`` and ``max_depth``; same-domain by default. Each
        page goes through the full pipeline; a page that fails to fetch or extract
        is recorded with its error and the crawl continues.
        """
        adapter = make_schema_adapter(schema_or_prompt, prompt=prompt)
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        items: list[CrawlItem] = []

        while queue and len(items) < max_pages:
            url, depth = queue.popleft()
            key = url.rstrip("/")
            if key in visited:
                continue
            visited.add(key)
            try:
                fetch_result = await self.fetch(url)
                extraction = await self._extract_with_quality_retry(fetch_result, adapter)
                data = adapter.model.model_validate(extraction.data) if adapter.model else extraction.data
                items.append(
                    CrawlItem(
                        url=url,
                        depth=depth,
                        ok=True,
                        data=data,
                        confidence=extraction.confidence.overall,
                        cost_usd=extraction.cost_usd,
                    )
                )
                if depth < max_depth:
                    for link in extract_links(fetch_result.html, fetch_result.final_url, same_domain=same_domain):
                        if link.rstrip("/") not in visited:
                            queue.append((link, depth + 1))
            except Exception as exc:
                self.logger.info("crawl page failed", extra={"extra": {"url": url, "error": str(exc)}})
                items.append(CrawlItem(url=url, depth=depth, ok=False, error=str(exc)))

        return CrawlReport(start_url=start_url, items=items)

    async def extract_image(
        self,
        source: str | bytes,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        media_type: str | None = None,
        include_metadata: bool = False,
    ) -> T | dict[str, Any] | DaveExtraction:
        """Extract structured data from an image (path or raw bytes) using a vision model."""
        if isinstance(source, (bytes, bytearray)):
            image_bytes = bytes(source)
            resolved_media = media_type or "image/png"
            final_url = "image"
        else:
            path = Path(str(source)).expanduser()
            if not path.exists() or not path.is_file():
                raise FetchError(f"Image not found: {path}")
            image_bytes = path.read_bytes()
            resolved_media = media_type or mimetypes.guess_type(str(path))[0] or "image/png"
            final_url = path.as_uri()

        adapter = make_schema_adapter(schema_or_prompt, prompt=prompt)
        extractor = VisionExtractor(self.config, cost_tracker=self.cost_tracker)
        extraction = await extractor.extract(image_bytes, adapter, media_type=resolved_media)
        output = adapter.model.model_validate(extraction.data) if adapter.model else extraction.data
        if include_metadata:
            return DaveExtraction(
                data=output,
                confidence=extraction.confidence.overall,
                field_confidence={field.field: field.score for field in extraction.confidence.fields},
                evidence=extraction.evidence,
                cost_usd=extraction.cost_usd,
                fetcher="vision",
                final_url=final_url,
            )
        return output

    async def search(
        self,
        query: str,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        provider: BaseSearchProvider | str | None = None,
        limit: int = 5,
        include_metadata: bool = False,
        force_refresh: bool = False,
    ) -> SearchReport:
        """Search the web for a query and run extraction over each result.

        Failures on a single URL are isolated: that result is marked failed with
        its error and the rest of the batch continues.
        """
        search_provider = self._resolve_search_provider(provider)
        hits = await search_provider.search(query, limit=limit)
        items: list[SearchResultItem] = []
        for hit in hits:
            try:
                data = await self.extract(
                    hit.url,
                    schema_or_prompt,
                    prompt=prompt,
                    include_metadata=include_metadata,
                    force_refresh=force_refresh,
                )
                items.append(SearchResultItem(hit=hit, ok=True, data=data))
            except Exception as exc:
                self.logger.info("search extract failed", extra={"extra": {"url": hit.url, "error": str(exc)}})
                items.append(SearchResultItem(hit=hit, ok=False, error=str(exc)))
        return SearchReport(query=query, provider=search_provider.name, items=items)

    def _resolve_search_provider(self, provider: BaseSearchProvider | str | None) -> BaseSearchProvider:
        if provider is None:
            provider = self.config.search_provider
        if isinstance(provider, BaseSearchProvider):
            return provider
        if isinstance(provider, str):
            return get_search_provider(provider, config=self.config)
        raise TypeError("provider must be a search provider name, instance, or None")

    async def stream_extract(
        self,
        url: str,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        force_refresh: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        """Stream extraction progress and fields as they become available."""
        adapter = make_schema_adapter(schema_or_prompt, prompt=prompt)
        yield StreamEvent("fetch_started", "Fetching page", {"url": url})
        fetch_result = await self.fetch(url, force_refresh=force_refresh)
        estimate = self.estimate_cost_from_text(self._content_for_extraction(fetch_result), adapter)
        yield StreamEvent(
            "cost_estimated",
            "Estimated extraction cost",
            {"tokens": estimate.total_tokens, "cost_usd": estimate.cost_usd, "fetcher": fetch_result.fetcher},
        )
        yield StreamEvent("extraction_started", "Extracting structured data", {"chunks": self._estimated_chunks(fetch_result)})
        extraction = await self._extract_with_quality_retry(fetch_result, adapter)
        for key, value in extraction.data.items():
            yield StreamEvent("field", f"Extracted {key}", {"field": key, "value": value})
        yield StreamEvent(
            "complete",
            "Extraction complete",
            {
                "data": extraction.data,
                "confidence": extraction.confidence.overall,
                "cost_usd": extraction.cost_usd,
                "evidence": extraction.evidence,
            },
        )

    async def estimate_cost(
        self,
        url: str,
        schema_or_prompt: type[T] | str | None = None,
        *,
        prompt: str | None = None,
        force_refresh: bool = False,
    ) -> CostEstimate:
        """Fetch or reuse page text and estimate extraction cost before calling the model."""
        adapter = make_schema_adapter(schema_or_prompt, prompt=prompt)
        fetch_result = await self.fetch(url, force_refresh=force_refresh)
        return self.estimate_cost_from_text(self._content_for_extraction(fetch_result), adapter, cached_fetch=not force_refresh)

    def estimate_cost_from_text(self, text: str, adapter: Any, *, cached_fetch: bool = False) -> CostEstimate:
        """Estimate cost from text and a schema adapter."""
        prompt_tokens = estimate_tokens(text) + estimate_tokens(adapter.prompt) + estimate_tokens(schema_prompt(adapter))
        completion_tokens = max(250, min(2_000, prompt_tokens // 3))
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        tracker = CostTracker()
        cost = tracker.estimate_cost(self.config.llm.provider, self.config.llm.model, usage)
        return CostEstimate(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost,
            cached_fetch=cached_fetch,
        )

    async def fetch(self, url: str, *, force_refresh: bool = False) -> FetchResult:
        """Fetch a URL with cache, rate limiting, retries, and automatic backend selection."""
        cache_key = CacheStore.make_key(url, self.config.fetcher)
        if self.cache and not force_refresh:
            cached = self.cache.get("fetch", cache_key)
            if cached is not None:
                return FetchResult.from_dict(cached)

        if self.config.respect_robots_txt and not is_local_source(url):
            robots_agent = self.user_agents.get() if self.config.antibot.rotate_user_agents else "DAVE"
            if not await self.robots.allowed(url, robots_agent):
                raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")

        await self.rate_limiter.wait(url)
        delay = self.delay_policy.next_delay()
        if delay > 0:
            await asyncio.sleep(delay)

        user_agent = self.user_agents.get() if self.config.antibot.rotate_user_agents else None
        request = FetchRequest(
            url=url,
            timeout_seconds=self.config.timeout_seconds,
            headers=random_headers(user_agent),
            proxy=self.proxies.next(),
            user_agent=user_agent,
            render_js=self._should_render_js(url),
        )
        fetcher_name = self._select_fetcher(url)
        result = await self._fetch_with_retries(fetcher_name, request)
        if detect_captcha(result.html, result.text):
            raise CaptchaDetectedError(f"CAPTCHA or bot challenge detected at {url}")
        if self.cache:
            self.cache.set("fetch", cache_key, result.to_dict())
        return result

    async def _fetch_with_retries(self, fetcher_name: str, request: FetchRequest) -> FetchResult:
        last_error: Exception | None = None
        for attempt in range(self.config.retries + 1):
            try:
                fetcher = self.fetchers[fetcher_name]
                result = await fetcher.fetch(request)
                self.proxies.mark_success(request.proxy)
                return result
            except Exception as exc:
                last_error = exc
                self.proxies.mark_failure(request.proxy)
                if attempt < self.config.retries:
                    await asyncio.sleep(min(2**attempt, 8))
        raise FetchError(f"Failed to fetch {request.url}: {last_error}") from last_error

    async def _extract_with_quality_retry(self, fetch_result: FetchResult, adapter: Any) -> ExtractionResult:
        last_result: ExtractionResult | None = None
        for attempt in range(self.config.max_low_confidence_retries + 1):
            result = await self.extractor.extract(self._content_for_extraction(fetch_result), adapter)
            last_result = result
            if result.confidence.overall >= self.config.min_confidence:
                return result
            self.logger.info("low confidence extraction", extra={"extra": {"attempt": attempt, "confidence": result.confidence.overall}})
        assert last_result is not None
        raise LowConfidenceError(
            f"Extraction confidence {last_result.confidence.overall} is below required {self.config.min_confidence}"
        )

    def _select_fetcher(self, url: str) -> str:
        if self.config.fetcher != "auto":
            if self.config.fetcher in {"firecrawl", "crawl4ai"}:
                raise FetchError(f"{self.config.fetcher} integration is configured as optional and is not installed in this build")
            if self.config.fetcher not in self.fetchers:
                known = ", ".join(sorted(self.fetchers))
                raise FetchError(
                    f"Unknown fetcher {self.config.fetcher!r}. Available fetchers: {known}. "
                    "Register plugin fetchers with dave.plugins.register_fetcher() before use."
                )
            return self.config.fetcher
        if is_local_source(url):
            return "file"
        if self._should_render_js(url):
            return "playwright"
        return "http"

    def _should_render_js(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        spa_markers = ("app", "dashboard", "pricing", "products")
        return any(marker in path for marker in spa_markers) and self.config.fetcher == "auto"

    def _content_for_extraction(self, fetch_result: FetchResult) -> str:
        """Return the richest extraction context available for a fetched page."""
        if fetch_result.html and fetch_result.text and fetch_result.html != fetch_result.text:
            return f"{fetch_result.html}\n\n{fetch_result.text}"
        return fetch_result.text or fetch_result.html

    def _estimated_chunks(self, fetch_result: FetchResult) -> int:
        text = self._content_for_extraction(fetch_result)
        return max(1, min(self.config.max_chunks, (len(text) + self.config.chunk_size_chars - 1) // self.config.chunk_size_chars))

    @staticmethod
    def diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        """Return a simple field-level diff for monitoring changed extractions."""
        changes: dict[str, Any] = {}
        keys = set(previous) | set(current)
        for key in sorted(keys):
            before = previous.get(key)
            after = current.get(key)
            if before != after:
                changes[key] = {"before": before, "after": after}
        return changes

    @staticmethod
    def to_json(data: Any) -> str:
        """Serialize Pydantic models or dictionaries as pretty JSON."""
        if isinstance(data, DaveExtraction):
            payload = {
                "data": data.data.model_dump() if hasattr(data.data, "model_dump") else data.data,
                "confidence": data.confidence,
                "field_confidence": data.field_confidence,
                "evidence": data.evidence,
                "cost_usd": data.cost_usd,
                "fetcher": data.fetcher,
                "final_url": data.final_url,
            }
        elif hasattr(data, "model_dump"):
            payload = data.model_dump()
        elif is_dataclass(data):
            payload = asdict(data)
        else:
            payload = data
        return json.dumps(payload, indent=2, sort_keys=True)
