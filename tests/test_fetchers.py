from __future__ import annotations

import pytest

from dave.fetchers.base import FetchRequest
from dave.fetchers.http import HttpFetcher


@pytest.mark.asyncio
async def test_http_fetcher_extracts_text(httpx_mock):
    html = "<html><head><title>Hello</title><script>bad()</script></head><body><h1>Hello World</h1></body></html>"
    httpx_mock.add_response(url="https://example.test", text=html, status_code=200)

    result = await HttpFetcher().fetch(FetchRequest(url="https://example.test"))

    assert result.status_code == 200
    assert result.fetcher == "http"
    assert "Hello World" in result.text
    assert "bad()" not in result.text
