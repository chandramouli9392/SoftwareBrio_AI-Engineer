"""Multi-page crawling.

Give DAVE a starting URL and it follows links across the site, running the full
extraction pipeline on each page — the multi-page capability general extractors
lack. Crawling reuses every engine control: cache, retries, rate limits,
robots.txt, and confidence scoring all apply per page. Breadth-first, bounded by
page count and depth, same-domain by default.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

_ASSET_SUFFIXES = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".zip", ".gz", ".mp4", ".mp3", ".css", ".js", ".woff", ".woff2", ".ttf",
)
_SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:")


def extract_links(html: str, base_url: str, *, same_domain: bool = True) -> list[str]:
    """Return absolute, deduped, crawlable links found in ``html``.

    Resolves relative URLs against ``base_url``, drops fragments, mail/tel/JS
    links, and static assets, and (by default) keeps only same-domain links.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc
    out: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(_SKIP_PREFIXES):
            continue
        url, _ = urldefrag(urljoin(base_url, href))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if same_domain and parsed.netloc != base_host:
            continue
        if parsed.path.lower().endswith(_ASSET_SUFFIXES):
            continue
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _serialize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _serialize(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return str(value)


@dataclass(slots=True)
class CrawlItem:
    """Extraction outcome for one crawled page."""

    url: str
    depth: int
    ok: bool
    data: Any = None
    confidence: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None


@dataclass(slots=True)
class CrawlReport:
    """Aggregated results from a crawl."""

    start_url: str
    items: list[CrawlItem]

    @property
    def ok_items(self) -> list[CrawlItem]:
        """Only the pages that extracted successfully."""
        return [item for item in self.items if item.ok]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a JSON-ready dictionary."""
        return {
            "start_url": self.start_url,
            "pages": len(self.items),
            "ok_pages": len(self.ok_items),
            "total_cost_usd": round(sum(item.cost_usd for item in self.items), 6),
            "results": [
                {
                    "url": item.url,
                    "depth": item.depth,
                    "ok": item.ok,
                    "data": _serialize(item.data) if item.ok else None,
                    "confidence": item.confidence,
                    "cost_usd": item.cost_usd,
                    "error": item.error,
                }
                for item in self.items
            ],
        }
