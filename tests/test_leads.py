from __future__ import annotations

import pytest

from dave.core.errors import LeadsConfigError
from dave.leads import Lead, LeadsReport, find_leads

SAMPLE = [
    {
        "title": "Bold Roofing",
        "phone": "(972) 380-9300",
        "website": "https://www.boldroofing.com/",
        "address": "10720 Miller Rd #303, Dallas, TX 75238",
        "categoryName": "Roofing contractor",
        "totalScore": 4.7,
        "reviewsCount": 607,
        "url": "https://maps.google.com/?cid=123",
    },
    {"title": "No Phone Co", "phone": "", "website": "x.com"},          # dropped: no phone
    {"title": "", "phone": "555-1212"},                                  # dropped: no name
    {"title": "Bold Roofing", "phone": "(972) 380-9300"},               # dropped: duplicate
    {"title": "Acme Plumbing", "phoneUnformatted": "+12145551234", "categoryName": "Plumber"},
]


@pytest.mark.asyncio
async def test_find_leads_maps_filters_and_dedupes(httpx_mock):
    httpx_mock.add_response(json=SAMPLE)
    report = await find_leads("roofing companies", "Dallas, TX", api_key="test-token", max_results=10)
    assert isinstance(report, LeadsReport)
    assert len(report.leads) == 2  # only ones with name + phone, deduped
    bold = report.leads[0]
    assert bold.business_name == "Bold Roofing"
    assert bold.phone == "(972) 380-9300"
    assert bold.website == "boldroofing.com"          # protocol + www stripped
    assert bold.category == "Roofing contractor"
    assert bold.rating == 4.7 and bold.reviews_count == 607
    assert bold.status == "To contact"


@pytest.mark.asyncio
async def test_find_leads_sends_right_apify_query(httpx_mock):
    httpx_mock.add_response(json=SAMPLE)
    await find_leads("med spas", "Scottsdale, AZ", api_key="tok", max_results=5)
    import json as _json
    req = httpx_mock.get_requests()[0]
    assert "compass~crawler-google-places" in str(req.url)
    body = _json.loads(req.read())
    assert body["searchStringsArray"] == ["med spas in Scottsdale, AZ"]
    assert body["maxCrawledPlacesPerSearch"] == 5


@pytest.mark.asyncio
async def test_find_leads_requires_key(monkeypatch):
    monkeypatch.delenv("APIFY_API_KEY", raising=False)
    with pytest.raises(LeadsConfigError, match="APIFY_API_KEY"):
        await find_leads("x", "y")


def test_leads_report_to_csv_has_headers_and_rows():
    leads = [Lead(business_name="Bold Roofing", phone="(972) 380-9300", website="boldroofing.com",
                  address="Dallas, TX", category="Roofing contractor", rating=4.7, reviews_count=607,
                  maps_url="https://maps.google.com/?cid=1")]
    csv = LeadsReport(industry="roofing", city="Dallas", leads=leads).to_csv()
    lines = csv.strip().splitlines()
    assert lines[0].startswith("Business Name,Phone,Website")
    assert "Bold Roofing" in lines[1] and "(972) 380-9300" in lines[1]
    assert "To contact" in lines[1]


def test_top_level_find_leads_helper_exists():
    import dave
    assert hasattr(dave, "find_leads")
