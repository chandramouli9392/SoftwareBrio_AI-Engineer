"""Comprehensive tests for SoftwareBrio Autonomous Lead Enrichment Agent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.core.errors import FetchError
from dave.enrichment.agent import LeadEnrichmentAgent
from dave.enrichment.cleaner import clean_html
from dave.enrichment.discovery import (
    InformationGoal,
    discover_relevant_pages,
)
from dave.enrichment.schema import (
    CompanyEnrichment,
    ContactPoint,
    EnrichmentStatus,
    LeadershipMember,
)
from dave.enrichment.scorer import calculate_confidence_score, determine_status
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult

# =====================================================================
# 1. SCHEMA & VALIDATION TESTS
# =====================================================================

def test_company_enrichment_schema_valid() -> None:
    enrichment = CompanyEnrichment(
        domain="postman.com",
        company_overview="Postman is an API platform for building and using APIs.",
        target_audience="Software developers, API architects, and engineering teams.",
        contact_points=[
            ContactPoint(email="sales@postman.com", type="sales", source_url="https://postman.com/contact")
        ],
        leadership=[
            LeadershipMember(name="Abhinav Asthana", role="CEO & Co-founder", linkedin_url="https://linkedin.com/in/abhinav-asthana")
        ],
        confidence_score=0.85,
        source_pages=["https://postman.com", "https://postman.com/about"],
        status=EnrichmentStatus.SUCCESS,
        errors=[],
    )
    dumped = enrichment.model_dump()
    assert dumped["domain"] == "postman.com"
    assert dumped["confidence_score"] == 0.85
    assert dumped["status"] == "success"
    assert len(dumped["contact_points"]) == 1
    assert len(dumped["leadership"]) == 1


def test_confidence_score_boundaries() -> None:
    # Score must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        CompanyEnrichment(domain="test.com", confidence_score=1.5)

    with pytest.raises(ValidationError):
        CompanyEnrichment(domain="test.com", confidence_score=-0.1)

    # Valid boundary scores
    c_zero = CompanyEnrichment(domain="test.com", confidence_score=0.0)
    assert c_zero.confidence_score == 0.0

    c_one = CompanyEnrichment(domain="test.com", confidence_score=1.0)
    assert c_one.confidence_score == 1.0


# =====================================================================
# 2. CONTENT CLEANER TESTS
# =====================================================================

def test_content_cleaner_removes_scripts_styles_and_svgs() -> None:
    html = """
    <html>
        <head>
            <style>body { font-size: 14px; }</style>
            <script>console.log("tracking code");</script>
        </head>
        <body>
            <svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>
            <h1>Real Company Heading</h1>
            <p>We build production AI engines.</p>
            <noscript>Enable JS</noscript>
        </body>
    </html>
    """
    clean = clean_html(html)
    assert "console.log" not in clean
    assert "circle" not in clean
    assert "font-size" not in clean
    assert "Enable JS" not in clean
    assert "# Real Company Heading" in clean
    assert "We build production AI engines." in clean


def test_content_cleaner_removes_noise_cookie_banners_and_nav() -> None:
    html = """
    <div>
        <div class="cookie-banner-consent modal-overlay">
            <p>We use cookies to enhance your experience. Click Accept.</p>
            <button>Accept</button>
        </div>
        <nav role="navigation">
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/login">Login</a></li>
            </ul>
        </nav>
        <main>
            <h1>Postman Enterprise</h1>
            <p>Collaborative API development environment for modern teams.</p>
        </main>
    </div>
    """
    clean = clean_html(html)
    assert "We use cookies" not in clean
    assert "# Postman Enterprise" in clean
    assert "Collaborative API development environment" in clean


def test_content_cleaner_preserves_tables_and_lists() -> None:
    html = """
    <h2>Pricing Plans</h2>
    <table>
        <tr><th>Plan</th><th>Price</th></tr>
        <tr><td>Free</td><td>$0</td></tr>
        <tr><td>Enterprise</td><td>Custom</td></tr>
    </table>
    <ul>
        <li>Automated Testing</li>
        <li>Mock Servers</li>
    </ul>
    """
    clean = clean_html(html)
    assert "## Pricing Plans" in clean
    assert "| Plan | Price |" in clean
    assert "| Free | $0 |" in clean
    assert "- Automated Testing" in clean
    assert "- Mock Servers" in clean


def test_content_cleaner_preserves_mailto_and_linkedin_links() -> None:
    html = """
    <div class="footer">
        <p>Get in touch with our team:</p>
        <a href="mailto:hello@supabase.com">Email Hello</a>
        <a href="https://linkedin.com/company/supabase">Supabase LinkedIn</a>
    </div>
    """
    clean = clean_html(html)
    assert "hello@supabase.com" in clean
    assert "https://linkedin.com/company/supabase" in clean


# =====================================================================
# 3. PAGE DISCOVERY & RANKING TESTS
# =====================================================================

def test_page_discovery_ranking() -> None:
    homepage_html = """
    <html>
        <body>
            <a href="/about-us">About Us</a>
            <a href="/team">Leadership & Team</a>
            <a href="/pricing">Pricing Plans</a>
            <a href="/contact">Contact Sales</a>
            <a href="/blog/2023/10/how-we-built-our-infra">Blog Post</a>
            <a href="/legal/privacy-policy">Privacy Policy</a>
            <a href="https://external.com">External Link</a>
        </body>
    </html>
    """
    candidates = discover_relevant_pages(
        homepage_html,
        base_url="https://example.com",
        max_pages=5,
    )
    candidate_urls = [c.url for c in candidates]
    # Priority pages should be picked
    assert any("/team" in u for u in candidate_urls)
    assert any("/pricing" in u for u in candidate_urls)
    assert any("/contact" in u for u in candidate_urls)
    # Blog and legal should be deprioritized / not in top
    for u in candidate_urls[:3]:
        assert "/blog" not in u
        assert "/legal" not in u


def test_page_discovery_dynamic_needed_goals() -> None:
    homepage_html = """
    <html>
        <body>
            <a href="/team">Our Executive Team</a>
            <a href="/pricing">Pricing Tiers</a>
            <a href="/contact">Contact Page</a>
        </body>
    </html>
    """
    # When leadership is missing, leadership pages must receive top score
    candidates_leadership = discover_relevant_pages(
        homepage_html,
        base_url="https://example.com",
        needed_goals={InformationGoal.LEADERSHIP},
    )
    assert candidates_leadership[0].goal == InformationGoal.LEADERSHIP


# =====================================================================
# 4. CONFIDENCE SCORING & STATUS TESTS
# =====================================================================

def test_confidence_scoring_full_data() -> None:
    source_text = """
    Supabase is an open source Firebase alternative providing Postgres databases,
    authentication, and instant APIs. Designed for developers building web and mobile apps.
    Leadership: Paul Copplestone (CEO), Ant Wilson (CTO).
    Contact: sales@supabase.com. LinkedIn: https://linkedin.com/company/supabase
    """
    score = calculate_confidence_score(
        company_overview="Supabase is an open source Firebase alternative providing Postgres databases and APIs.",
        target_audience="Full-stack developers and engineering organizations.",
        contact_points=[
            ContactPoint(email="sales@supabase.com", type="sales", source_url="https://supabase.com")
        ],
        leadership=[
            LeadershipMember(name="Paul Copplestone", role="CEO", linkedin_url="https://linkedin.com/company/supabase"),
            LeadershipMember(name="Ant Wilson", role="CTO"),
        ],
        source_pages=["https://supabase.com", "https://supabase.com/about", "https://supabase.com/pricing"],
        aggregated_source_text=source_text,
    )
    assert 0.65 <= score <= 1.0

    status = determine_status(
        company_overview="Supabase is an open source Firebase alternative.",
        target_audience="Developers building modern apps.",
        contact_points=[ContactPoint(email="sales@supabase.com", type="sales", source_url="https://supabase.com")],
        leadership=[LeadershipMember(name="Paul Copplestone", role="CEO")],
        source_pages=["https://supabase.com"],
        confidence_score=score,
        errors=[],
    )
    assert status == EnrichmentStatus.SUCCESS


def test_confidence_scoring_partial_and_failed() -> None:
    # Partial: has overview and ICP, but no leadership/contacts
    score_partial = calculate_confidence_score(
        company_overview="Vapi provides voice AI infrastructure for developers.",
        target_audience="Developers building voice agents.",
        contact_points=[],
        leadership=[],
        source_pages=["https://vapi.ai"],
        aggregated_source_text="Vapi voice AI for developers.",
    )
    assert 0.20 <= score_partial <= 0.60
    status_partial = determine_status(
        company_overview="Vapi voice AI infrastructure.",
        target_audience="Developers.",
        contact_points=[],
        leadership=[],
        source_pages=["https://vapi.ai"],
        confidence_score=score_partial,
        errors=[],
    )
    assert status_partial == EnrichmentStatus.PARTIAL

    # Failed: no source pages or completely empty
    score_failed = calculate_confidence_score(
        company_overview="",
        target_audience="",
        contact_points=[],
        leadership=[],
        source_pages=[],
        aggregated_source_text="",
    )
    assert score_failed == 0.0
    status_failed = determine_status(
        company_overview="",
        target_audience="",
        contact_points=[],
        leadership=[],
        source_pages=[],
        confidence_score=0.0,
        errors=["Failed to reach host"],
    )
    assert status_failed == EnrichmentStatus.FAILED


# =====================================================================
# 5. AGENT ORCHESTRATION & FAILURE ISOLATION (MOCKED)
# =====================================================================

class MockHTMLFetcher(BaseFetcher):
    """Mock fetcher providing deterministic HTML responses."""

    def __init__(self, page_map: dict[str, str] | None = None, fail_urls: set[str] | None = None) -> None:
        self.page_map = page_map or {}
        self.fail_urls = fail_urls or set()

    async def fetch(self, request: FetchRequest) -> FetchResult:
        if request.url in self.fail_urls:
            raise FetchError(f"404 Not Found: {request.url}")

        html = self.page_map.get(
            request.url,
            f"<html><body><h1>Default Page</h1><p>Domain content for {request.url}</p></body></html>",
        )
        return FetchResult(
            url=request.url,
            final_url=request.url,
            status_code=200,
            headers={"content-type": "text/html"},
            html=html,
            text="Default Page Domain content",
            elapsed_seconds=0.05,
            fetcher="mock",
        )


@pytest.mark.asyncio
async def test_agent_enrich_company_mock() -> None:
    pages = {
        "https://postman.com": """
        <html><body>
            <h1>Postman API Platform</h1>
            <p>Postman is the world's leading API platform for building and using APIs.</p>
            <p>Target audience: Engineering teams and API developers.</p>
            <a href="https://postman.com/about">About Company</a>
            <a href="https://postman.com/contact">Contact Us</a>
        </body></html>
        """,
        "https://postman.com/about": """
        <html><body>
            <h2>Leadership Team</h2>
            <p>Abhinav Asthana is the CEO and Co-founder.</p>
            <a href="https://linkedin.com/in/abhinav-asthana">LinkedIn</a>
        </body></html>
        """,
        "https://postman.com/contact": """
        <html><body>
            <h2>Contact Postman</h2>
            <p>Reach out to sales at <a href="mailto:sales@postman.com">sales@postman.com</a>.</p>
        </body></html>
        """,
    }
    fetcher = MockHTMLFetcher(page_map=pages)
    config = DaveConfig(llm=LLMConfig(provider="mock", model="mock"), cache={"enabled": False, "directory": "/tmp/dave-test", "ttl_seconds": 60})
    engine = DaveEngine(config=config, fetchers={"http": fetcher, "playwright": fetcher})
    agent = LeadEnrichmentAgent(engine=engine)

    result = await agent.enrich_company("postman.com")
    assert result.domain == "postman.com"
    assert len(result.source_pages) >= 1
    assert result.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)
    # Check that email was discovered from text
    emails = [cp.email for cp in result.contact_points]
    assert "sales@postman.com" in emails


@pytest.mark.asyncio
async def test_agent_subpage_failure_resilience() -> None:
    # Homepage works, but discovered subpage 404s
    pages = {
        "https://supabase.com": """
        <html><body>
            <h1>Supabase</h1>
            <p>The open source Firebase alternative with Postgres.</p>
            <a href="https://supabase.com/team">Our Team</a>
        </body></html>
        """
    }
    fetcher = MockHTMLFetcher(page_map=pages, fail_urls={"https://supabase.com/team"})
    config = DaveConfig(llm=LLMConfig(provider="mock", model="mock"), cache={"enabled": False, "directory": "/tmp/dave-test", "ttl_seconds": 60})
    engine = DaveEngine(config=config, fetchers={"http": fetcher, "playwright": fetcher})
    agent = LeadEnrichmentAgent(engine=engine)

    result = await agent.enrich_company("supabase.com")
    assert result.domain == "supabase.com"
    # Subpage failure was handled gracefully without raising
    assert any("Failed to fetch discovered page" in e for e in result.errors)
    assert result.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)


@pytest.mark.asyncio
async def test_agent_batch_failure_isolation() -> None:
    # Company 1 succeeds, Company 2 fails completely (DNS/Connection failure), Company 3 succeeds
    pages = {
        "https://company-one.com": "<html><body><h1>One</h1><p>Platform for fintech.</p></body></html>",
        "https://company-three.com": "<html><body><h1>Three</h1><p>Platform for healthtech.</p></body></html>",
    }
    fetcher = MockHTMLFetcher(page_map=pages, fail_urls={"https://failing-company.com"})
    config = DaveConfig(retries=0, llm=LLMConfig(provider="mock", model="mock"), cache={"enabled": False, "directory": "/tmp/dave-test", "ttl_seconds": 60})
    engine = DaveEngine(config=config, fetchers={"http": fetcher, "playwright": fetcher})
    agent = LeadEnrichmentAgent(engine=engine)

    results, metrics = await agent.enrich_domains(
        ["company-one.com", "failing-company.com", "company-three.com"]
    )

    assert len(results) == 3
    assert results[0].domain == "company-one.com"
    assert results[0].status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)

    # Failing company isolated
    assert results[1].domain == "failing-company.com"
    assert results[1].status == EnrichmentStatus.FAILED
    assert any("Failed to fetch homepage" in e for e in results[1].errors)

    # Third company still processed
    assert results[2].domain == "company-three.com"
    assert results[2].status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)

    assert metrics.companies_processed == 3
    assert metrics.failed_count == 1
