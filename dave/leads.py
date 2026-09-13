"""Local business lead generation.

Turn an industry + city into a ready-to-dial list: real businesses with phone
numbers, addresses, ratings, and websites. Backed by the Apify Google Maps
scraper (``compass/crawler-google-places``) — the reliable source for clean
local-business data that general web scraping can't get (Google Maps blocks
direct scraping).

This is the discovery layer. Pair it with DAVE's extraction to enrich each
business's own website, or with an LLM to write cold-call summaries.

Needs an Apify API key (APIFY_API_KEY) — get one at
https://console.apify.com/account/integrations
"""

from __future__ import annotations

import csv as _csv
import io
import os
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from dave.core.errors import LeadsConfigError, LeadsRequestError

_ACTOR = "compass~crawler-google-places"
_APIFY_BASE = "https://api.apify.com/v2"

CSV_COLUMNS = ["Business Name", "Phone", "Website", "Address", "Category", "Rating", "Reviews", "Call Summary", "Status"]


@dataclass(slots=True)
class Lead:
    """A single dial-ready business lead."""

    business_name: str
    phone: str
    website: str = ""
    address: str = ""
    category: str = ""
    rating: float | None = None
    reviews_count: int | None = None
    maps_url: str = ""
    summary: str = ""
    status: str = "To contact"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_row(self) -> list[str]:
        return [
            self.business_name, self.phone, self.website, self.address, self.category,
            "" if self.rating is None else str(self.rating),
            "" if self.reviews_count is None else str(self.reviews_count),
            self.summary, self.status,
        ]


@dataclass(slots=True)
class LeadsReport:
    """A list of leads for one industry + city search."""

    industry: str
    city: str
    leads: list[Lead] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "industry": self.industry,
            "city": self.city,
            "count": len(self.leads),
            "leads": [lead.to_dict() for lead in self.leads],
        }

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = _csv.writer(buffer)
        writer.writerow(CSV_COLUMNS)
        for lead in self.leads:
            writer.writerow(lead.to_row())
        return buffer.getvalue()


def _clean_website(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        if not parsed.netloc:
            return raw
        host = parsed.netloc.removeprefix("www.")
        return host + (parsed.path if parsed.path not in ("", "/") else "")
    except ValueError:
        return raw


async def find_leads(
    industry: str,
    city: str,
    *,
    max_results: int = 20,
    api_key: str | None = None,
    timeout_seconds: float = 300.0,
) -> LeadsReport:
    """Find local businesses with phone numbers for ``industry`` in ``city``.

    Returns only businesses that have a phone (this is built for cold calling).
    Requires an Apify API key via ``api_key`` or the APIFY_API_KEY env var.
    """
    token = (api_key or os.getenv("APIFY_API_KEY") or "").strip()
    if not token:
        raise LeadsConfigError(
            "Local leads need an Apify API key. Set APIFY_API_KEY or pass api_key=. "
            "Get one at https://console.apify.com/account/integrations"
        )

    payload = {
        "searchStringsArray": [f"{industry} in {city}"],
        "maxCrawledPlacesPerSearch": max(1, min(max_results, 100)),
        "language": "en",
        "skipClosedPlaces": False,
        "scrapeContacts": False,
    }
    url = f"{_APIFY_BASE}/acts/{_ACTOR}/run-sync-get-dataset-items?token={token}"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        raise LeadsRequestError(f"Could not reach Apify: {exc}") from exc
    if response.status_code >= 400:
        raise LeadsRequestError(f"Apify returned {response.status_code}: {response.text[:200]}")

    items = response.json()
    leads: list[Lead] = []
    seen: set[str] = set()
    for place in items:
        name = str(place.get("title") or "").strip()
        phone = str(place.get("phone") or place.get("phoneUnformatted") or "").strip()
        if not name or not phone:
            continue
        key = f"{name}-{phone}".lower()
        if key in seen:
            continue
        seen.add(key)
        leads.append(
            Lead(
                business_name=name,
                phone=phone,
                website=_clean_website(place.get("website")),
                address=str(place.get("address") or place.get("street") or "").strip(),
                category=str(place.get("categoryName") or industry).strip(),
                rating=place.get("totalScore") if place.get("totalScore") is not None else place.get("rating"),
                reviews_count=place.get("reviewsCount"),
                maps_url=str(place.get("url") or ""),
            )
        )
    return LeadsReport(industry=industry, city=city, leads=leads)
