from __future__ import annotations

import pytest

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.core.errors import FetchError
from dave.fetchers.base import FetchRequest
from dave.fetchers.file import FileFetcher, is_local_source


@pytest.mark.asyncio
async def test_reads_plain_text_file(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("Hello from a local file.", encoding="utf-8")
    result = await FileFetcher().fetch(FetchRequest(url=str(f)))
    assert result.status_code == 200
    assert result.fetcher == "file"
    assert "Hello from a local file." in result.text


@pytest.mark.asyncio
async def test_reads_html_file_and_strips_text(tmp_path):
    f = tmp_path / "page.html"
    f.write_text("<html><title>Local Page</title><body><p>Body here</p></body></html>", encoding="utf-8")
    result = await FileFetcher().fetch(FetchRequest(url=str(f)))
    assert "<title>Local Page</title>" in result.html
    assert "Body here" in result.text


@pytest.mark.asyncio
async def test_file_url_scheme_is_supported(tmp_path):
    f = tmp_path / "data.md"
    f.write_text("# Heading\n\nSome markdown.", encoding="utf-8")
    result = await FileFetcher().fetch(FetchRequest(url=f.as_uri()))
    assert "Some markdown." in result.text


@pytest.mark.asyncio
async def test_missing_file_raises(tmp_path):
    with pytest.raises(FetchError, match="not found|No such"):
        await FileFetcher().fetch(FetchRequest(url=str(tmp_path / "nope.txt")))


@pytest.mark.asyncio
async def test_pdf_without_pypdf_raises_helpful_error(tmp_path, monkeypatch):
    def boom() -> object:
        raise FetchError("PDF support requires pypdf. Install the pdf extra: pip install 'dave-ai[pdf]'.")

    monkeypatch.setattr("dave.fetchers.file._load_pypdf", boom)
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    with pytest.raises(FetchError, match="pdf extra|pypdf"):
        await FileFetcher().fetch(FetchRequest(url=str(f)))


def test_is_local_source_detection(tmp_path):
    existing = tmp_path / "x.txt"
    existing.write_text("hi", encoding="utf-8")
    assert is_local_source(str(existing)) is True
    assert is_local_source(existing.as_uri()) is True
    assert is_local_source("report.pdf") is True
    assert is_local_source("https://example.com/page") is False
    assert is_local_source("http://example.com") is False


@pytest.mark.asyncio
async def test_engine_auto_routes_local_file(tmp_path):
    f = tmp_path / "company.txt"
    f.write_text("<title>Acme Corp</title> We build rockets.", encoding="utf-8")
    config = DaveConfig(
        fetcher="auto",
        cache={"enabled": False, "directory": str(tmp_path / "c"), "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.0,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    engine = DaveEngine(config=config)
    result = await engine.extract(str(f), "get the title", include_metadata=True)
    assert result.fetcher == "file"
