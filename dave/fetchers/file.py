"""Local file fetcher.

Extends DAVE's pipeline beyond URLs: point it at a local file (text, HTML,
Markdown, JSON, or PDF) and it returns the same FetchResult the web fetchers do,
so extraction, validation, confidence, and cost tracking all apply unchanged.

PDF support needs ``pypdf``, shipped through the optional ``pdf`` extra. Every
other format uses the standard library only.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from dave.core.errors import FetchError
from dave.fetchers.base import BaseFetcher, FetcherKind, FetchRequest, FetchResult

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".csv", ".log", ".rst", ".yaml", ".yml"}
_HTML_SUFFIXES = {".html", ".htm", ".xhtml"}
_KNOWN_SUFFIXES = _TEXT_SUFFIXES | _HTML_SUFFIXES | {".pdf"}


def _to_path(target: str) -> Path:
    """Resolve a file path from a plain path or a file:// URL."""
    parsed = urlparse(target)
    if parsed.scheme == "file":
        from urllib.request import url2pathname
        return Path(url2pathname(parsed.path))
    return Path(target).expanduser()


def is_local_source(target: str) -> bool:
    """True when a target should be read from disk rather than fetched over HTTP."""
    parsed = urlparse(target)
    if parsed.scheme == "file":
        return True
    if parsed.scheme in {"http", "https"}:
        return False
    path = Path(target).expanduser()
    if path.exists():
        return True
    return path.suffix.lower() in _KNOWN_SUFFIXES


def _load_pypdf() -> Any:
    """Import pypdf lazily so the core never requires it."""
    try:
        import pypdf
    except ImportError as exc:
        raise FetchError(
            "PDF support requires pypdf. Install the pdf extra with pip install 'dave-ai[pdf]'."
        ) from exc
    return pypdf


def _extract_pdf_text(path: Path) -> str:
    pypdf = _load_pypdf()
    reader = pypdf.PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()


class FileFetcher(BaseFetcher):
    """Read local files into the extraction pipeline."""

    kind = FetcherKind.FILE

    async def fetch(self, request: FetchRequest) -> FetchResult:
        path = _to_path(request.url)
        if not path.exists() or not path.is_file():
            raise FetchError(f"File not found: {path}")

        started = time.perf_counter()
        suffix = path.suffix.lower()
        html = ""
        if suffix == ".pdf":
            text = _extract_pdf_text(path)
        elif suffix in _HTML_SUFFIXES:
            html = path.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ").split())
        else:
            text = path.read_text(encoding="utf-8", errors="replace")

        elapsed = time.perf_counter() - started
        final_url = path.as_uri()
        return FetchResult(
            url=request.url,
            final_url=final_url,
            status_code=200,
            headers={"content-type": _content_type(suffix)},
            html=html or text,
            text=text,
            elapsed_seconds=elapsed,
            fetcher=self.kind.value,
        )


def _content_type(suffix: str) -> str:
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in _HTML_SUFFIXES:
        return "text/html"
    if suffix == ".json":
        return "application/json"
    return "text/plain"
