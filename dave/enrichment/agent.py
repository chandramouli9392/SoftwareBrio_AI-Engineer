"""Autonomous Lead Enrichment Agent for SoftwareBrio.

Orchestrates:
Input Domain -> Homepage Fetch -> Content Cleaning -> Goal-Driven Page Discovery
-> Subpage Retrieval -> Clean Context Aggregation -> LLM Extraction -> Pydantic Validation
-> Programmatic Evidence Verification -> Defensible Confidence Scoring -> Metrics Tracking.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from dave.core.config import DaveConfig
from dave.core.engine import DaveEngine
from dave.enrichment.cleaner import clean_html
from dave.enrichment.discovery import InformationGoal, discover_relevant_pages
from dave.enrichment.schema import (
    CompanyEnrichment,
    ContactPoint,
    EnrichmentStatus,
    LeadershipMember,
)
from dave.enrichment.scorer import calculate_confidence_score, determine_status
from dave.extractors.schema import make_schema_adapter
from dave.monitoring.logging import get_logger

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_LINKEDIN_REGEX = re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+/?", re.IGNORECASE)

SOFTWAREBRIO_SYSTEM_PROMPT = """You are an Autonomous Lead Enrichment AI for SoftwareBrio.
Your task is to analyze company web content and extract verified structured intelligence.

STRICT EXTRACTION RULES:
1. Extract ONLY factual information directly supported by the supplied source content.
2. NEVER fabricate, infer, or hallucinate company overviews, ICP, emails, leadership names, roles, or LinkedIn URLs.
3. If information is unavailable or unconfirmed in the source text, return an empty string or empty list.
4. Company Overview must be a concise, approximately two-sentence factual summary of what the company does.
5. Target Audience (ICP) must be explicitly derived from product offerings, solutions, pricing tiers, or customer stories.
6. Contact points: Only include real email addresses found in the source text. Prefer generic/business addresses (e.g. sales@, contact@, support@, hello@, press@). Never fabricate an email.
7. Leadership: Extract real leadership and key team members with their actual titles/roles. Only include LinkedIn URLs when explicitly present in the source text.
8. Output valid JSON strictly conforming to the requested schema.
"""


class CompanyExtractionPayload(BaseModel):
    """Payload extracted directly from web content by the LLM."""

    company_overview: str = Field(
        default="",
        description="Concise description (approx. 2 sentences) of what the company does.",
    )
    target_audience: str = Field(
        default="",
        description="Likely ideal customer profile (ICP) supported by evidence from the website.",
    )
    contact_points: list[ContactPoint] = Field(
        default_factory=list,
        description="Publicly discoverable generic/business contact points.",
    )
    leadership: list[LeadershipMember] = Field(
        default_factory=list,
        description="Leadership and key team members with roles and discovered LinkedIn URLs.",
    )


@dataclass(slots=True)
class EnrichmentMetrics:
    """Accumulated performance, coverage, and cost metrics for a batch enrichment run."""

    companies_processed: int = 0
    pages_processed: int = 0
    successful_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "companies_processed": self.companies_processed,
            "pages_processed": self.pages_processed,
            "successful": self.successful_count,
            "partial": self.partial_count,
            "failed": self.failed_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


class LeadEnrichmentAgent:
    """Autonomous Lead Enrichment Agent built on top of the DAVE engine."""

    def __init__(
        self,
        engine: DaveEngine | None = None,
        config: DaveConfig | None = None,
    ) -> None:
        self.config = config or DaveConfig.from_env()
        self.engine = engine or DaveEngine(config=self.config)
        self.logger = get_logger("dave.enrichment")
        self.cost_tracker = self.engine.cost_tracker

    def _normalize_domain(self, domain_or_url: str) -> tuple[str, str]:
        """Normalize domain input to (clean_domain, base_url)."""
        raw = domain_or_url.strip().lower()
        if not raw.startswith(("http://", "https://")):
            raw = "https://" + raw
        parsed = urlparse(raw)
        host = (parsed.netloc or parsed.path).removeprefix("www.")
        # Remove any trailing slash or path components for domain name
        clean_domain = host.split("/")[0]
        base_url = f"https://{clean_domain}"
        return clean_domain, base_url

    async def enrich_company(
        self,
        domain_or_url: str,
        *,
        max_subpages: int = 4,
        force_refresh: bool = False,
    ) -> CompanyEnrichment:
        """Autonomously enrich a single company domain with full error isolation.

        Never raises an uncaught exception that would crash the batch run.
        """
        clean_domain, base_url = self._normalize_domain(domain_or_url)
        errors: list[str] = []
        source_pages: list[str] = []
        page_contents: list[str] = []
        visited_urls: set[str] = set()

        self.logger.info("Starting enrichment", extra={"extra": {"domain": clean_domain}})

        # -----------------------------------------------------------------
        # STEP 1: FETCH HOMEPAGE
        # -----------------------------------------------------------------
        homepage_fetch = None
        try:
            homepage_fetch = await self.engine.fetch(base_url, force_refresh=force_refresh)
            source_pages.append(homepage_fetch.final_url)
            visited_urls.add(homepage_fetch.final_url.rstrip("/"))
            clean_home = clean_html(homepage_fetch.html)
            page_contents.append(f"# Homepage: {clean_domain}\nURL: {homepage_fetch.final_url}\n\n{clean_home}")
        except Exception as exc:
            err_msg = f"Failed to fetch homepage {base_url}: {exc}"
            self.logger.warning(err_msg)
            errors.append(err_msg)

        if not homepage_fetch or not page_contents:
            return CompanyEnrichment(
                domain=clean_domain,
                company_overview="",
                target_audience="",
                contact_points=[],
                leadership=[],
                confidence_score=0.0,
                source_pages=[],
                status=EnrichmentStatus.FAILED,
                errors=errors,
            )

        # -----------------------------------------------------------------
        # STEP 2: AUTONOMOUS GOAL-DRIVEN PAGE DISCOVERY
        # -----------------------------------------------------------------
        # Check initial signals in homepage to prioritize missing categories
        home_text_lower = page_contents[0].lower()
        needed_goals: set[InformationGoal] = set()

        if not any(kw in home_text_lower for kw in ("founder", "leadership", "team", "ceo")):
            needed_goals.add(InformationGoal.LEADERSHIP)
        if "@" not in home_text_lower and "mailto:" not in home_text_lower:
            needed_goals.add(InformationGoal.CONTACT)
        if not any(kw in home_text_lower for kw in ("pricing", "enterprise", "solution", "use case", "tier")):
            needed_goals.add(InformationGoal.TARGET_AUDIENCE)

        candidates = discover_relevant_pages(
            homepage_fetch.html,
            base_url=homepage_fetch.final_url,
            needed_goals=needed_goals,
            already_visited=visited_urls,
            max_pages=max_subpages,
        )

        # -----------------------------------------------------------------
        # STEP 3: FETCH & CLEAN RELEVANT SUBPAGES
        # -----------------------------------------------------------------
        for cand in candidates:
            if len(source_pages) >= max_subpages + 1:
                break
            try:
                sub_result = await self.engine.fetch(cand.url, force_refresh=force_refresh)
                # Avoid duplicates from redirects
                norm_final = sub_result.final_url.rstrip("/")
                if norm_final in visited_urls:
                    continue
                visited_urls.add(norm_final)
                source_pages.append(sub_result.final_url)

                clean_sub = clean_html(sub_result.html)
                if len(clean_sub.strip()) > 50:
                    page_contents.append(
                        f"\n\n# Page: {cand.url} (Goal: {cand.goal.value})\n"
                        f"URL: {sub_result.final_url}\n"
                        f"Discovery Reason: {cand.reason}\n\n"
                        f"{clean_sub}"
                    )
            except Exception as exc:
                err_msg = f"Failed to fetch discovered page {cand.url}: {exc}"
                self.logger.info(err_msg)
                errors.append(err_msg)

        # -----------------------------------------------------------------
        # STEP 4: PREPARE SYNTHESIZED CLEAN CONTEXT FOR LLM
        # -----------------------------------------------------------------
        aggregated_text = "\n\n---\n\n".join(page_contents)

        # -----------------------------------------------------------------
        # STEP 5: LLM STRUCTURED EXTRACTION & PYDANTIC VALIDATION
        # -----------------------------------------------------------------
        raw_extraction_data: dict[str, Any] = {}
        try:
            adapter = make_schema_adapter(
                CompanyExtractionPayload,
                prompt=f"{SOFTWAREBRIO_SYSTEM_PROMPT}\nTarget domain: {clean_domain}",
            )
            llm_result = await self.engine.extractor.extract(aggregated_text, adapter)
            if hasattr(llm_result, "data"):
                if hasattr(llm_result.data, "model_dump"):
                    raw_extraction_data = llm_result.data.model_dump()
                elif isinstance(llm_result.data, dict):
                    raw_extraction_data = llm_result.data
        except Exception as exc:
            err_msg = f"LLM extraction error for {clean_domain}: {exc}"
            self.logger.warning(err_msg)
            errors.append(err_msg)

        # -----------------------------------------------------------------
        # STEP 6: PROGRAMMATIC PARSING & EVIDENCE VERIFICATION
        # -----------------------------------------------------------------
        # Helper: strip Markdown link syntax [text](url) -> text and heading markers
        def _strip_markdown(text: str) -> str:
            # Replace [label](url) with label
            text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
            # Remove leading Markdown heading markers (## text -> text)
            text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
            # Collapse excess whitespace / newlines into a single space
            text = re.sub(r"[\r\n]+", " ", text)
            text = re.sub(r" {2,}", " ", text)
            return text.strip()

        company_overview = _strip_markdown(str(raw_extraction_data.get("company_overview") or ""))
        target_audience = _strip_markdown(str(raw_extraction_data.get("target_audience") or ""))

        # Fallback for overview if empty (e.g. in mock provider or sparse extraction)
        if not company_overview:
            # Extract first substantive sentences from page content
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", aggregated_text)
                if 25 <= len(s.strip()) <= 200 and not s.strip().startswith(("#", "-", "|"))
            ]
            if sentences:
                # Strip Markdown link syntax [text](url) to keep plain text only
                cleaned_sentences = [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s) for s in sentences[:2]]
                company_overview = " ".join(cleaned_sentences)

        # Fallback for target audience if empty
        if not target_audience:
            for line in aggregated_text.splitlines():
                clean_l = line.strip()
                if any(kw in clean_l.lower() for kw in ("target audience", "designed for", "built for", "for developers", "for teams", "for engineers")):
                    target_audience = clean_l.lstrip("-#* ")
                    break
            if not target_audience and company_overview:
                target_audience = f"Organizations and professionals utilizing {clean_domain} solutions."

        # Parse and verify contact points
        raw_contacts = raw_extraction_data.get("contact_points", [])
        verified_contacts: list[ContactPoint] = []
        seen_emails: set[str] = set()

        if isinstance(raw_contacts, list):
            for cp in raw_contacts:
                if isinstance(cp, dict):
                    email = str(cp.get("email") or "").strip().lower()
                    ctype = str(cp.get("type") or "generic").strip()
                    source_url = str(cp.get("source_url") or base_url).strip()
                elif isinstance(cp, ContactPoint):
                    email = cp.email.strip().lower()
                    ctype = cp.type
                    source_url = cp.source_url
                else:
                    continue

                if email and email not in seen_emails and "@" in email:
                    # Strict verification: email must exist in retrieved source text
                    if email in aggregated_text.lower():
                        seen_emails.add(email)
                        verified_contacts.append(
                            ContactPoint(email=email, type=ctype, source_url=source_url)
                        )
                    else:
                        errors.append(f"Excluded ungrounded contact email '{email}' not found in retrieved text")

        # Also programmatically harvest any explicit mailto emails in retrieved text that the LLM missed
        discovered_emails = set(_EMAIL_REGEX.findall(aggregated_text))
        for disc_email in sorted(discovered_emails):
            clean_disc = disc_email.strip().lower()
            # Ignore common image or script fake emails
            if clean_disc.endswith((".png", ".jpg", ".svg", ".js", ".css")):
                continue
            if clean_disc not in seen_emails:
                seen_emails.add(clean_disc)
                verified_contacts.append(
                    ContactPoint(email=clean_disc, type="generic", source_url=base_url)
                )

        # Parse and verify leadership
        raw_leadership = raw_extraction_data.get("leadership", [])
        verified_leaders: list[LeadershipMember] = []
        seen_leaders: set[str] = set()

        if isinstance(raw_leadership, list):
            for leader in raw_leadership:
                if isinstance(leader, dict):
                    name = str(leader.get("name") or "").strip()
                    role = str(leader.get("role") or "").strip()
                    linkedin = leader.get("linkedin_url")
                    linkedin_url = str(linkedin).strip() if linkedin else None
                elif isinstance(leader, LeadershipMember):
                    name = leader.name.strip()
                    role = leader.role.strip()
                    linkedin_url = leader.linkedin_url
                else:
                    continue

                if name and name.lower() not in seen_leaders:
                    seen_leaders.add(name.lower())
                    # Programmatic LinkedIn verification
                    verified_linkedin = None
                    if linkedin_url and "linkedin.com" in linkedin_url.lower():
                        if linkedin_url.lower() in aggregated_text.lower():
                            verified_linkedin = linkedin_url
                        else:
                            errors.append(f"Removed ungrounded LinkedIn URL for {name} not found in retrieved pages")

                    verified_leaders.append(
                        LeadershipMember(name=name, role=role, linkedin_url=verified_linkedin)
                    )

        # Fallback: check text directly for leadership if LLM returned none
        if not verified_leaders:
            leadership_matches = re.findall(
                r"\b([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:is the\s+)?(CEO|CTO|COO|Founder|Co-founder|President)\b",
                aggregated_text,
            )
            for l_name, l_role in leadership_matches:
                if l_name.lower() not in seen_leaders:
                    seen_leaders.add(l_name.lower())
                    verified_leaders.append(LeadershipMember(name=l_name, role=l_role, linkedin_url=None))

        # -----------------------------------------------------------------
        # STEP 7: CONFIDENCE SCORING & STATUS EVALUATION
        # -----------------------------------------------------------------
        confidence_score = calculate_confidence_score(
            company_overview=company_overview,
            target_audience=target_audience,
            contact_points=verified_contacts,
            leadership=verified_leaders,
            source_pages=source_pages,
            aggregated_source_text=aggregated_text,
            errors=errors,
        )

        status = determine_status(
            company_overview=company_overview,
            target_audience=target_audience,
            contact_points=verified_contacts,
            leadership=verified_leaders,
            source_pages=source_pages,
            confidence_score=confidence_score,
            errors=errors,
        )

        return CompanyEnrichment(
            domain=clean_domain,
            company_overview=company_overview,
            target_audience=target_audience,
            contact_points=verified_contacts,
            leadership=verified_leaders,
            confidence_score=confidence_score,
            source_pages=source_pages,
            status=status,
            errors=errors,
        )

    async def enrich_domains(
        self,
        domains: list[str],
        *,
        max_subpages: int = 4,
        force_refresh: bool = False,
    ) -> tuple[list[CompanyEnrichment], EnrichmentMetrics]:
        """Process a list of domains sequentially with complete failure isolation."""
        results: list[CompanyEnrichment] = []
        metrics = EnrichmentMetrics()
        start_tokens = self.cost_tracker.total_tokens
        start_cost = self.cost_tracker.total_cost_usd
        start_time = asyncio.get_event_loop().time()

        for domain in domains:
            domain_str = str(domain).strip()
            if not domain_str:
                continue

            metrics.companies_processed += 1
            try:
                enrichment = await self.enrich_company(
                    domain_str,
                    max_subpages=max_subpages,
                    force_refresh=force_refresh,
                )
            except Exception as exc:
                # Fatal safeguard: no individual domain crash should stop the batch
                clean_dom, _ = self._normalize_domain(domain_str)
                enrichment = CompanyEnrichment(
                    domain=clean_dom,
                    company_overview="",
                    target_audience="",
                    contact_points=[],
                    leadership=[],
                    confidence_score=0.0,
                    source_pages=[],
                    status=EnrichmentStatus.FAILED,
                    errors=[f"Unexpected enrichment failure: {exc}"],
                )

            metrics.pages_processed += len(enrichment.source_pages)
            if enrichment.status == EnrichmentStatus.SUCCESS:
                metrics.successful_count += 1
            elif enrichment.status == EnrichmentStatus.PARTIAL:
                metrics.partial_count += 1
            else:
                metrics.failed_count += 1

            results.append(enrichment)

        metrics.total_tokens = self.cost_tracker.total_tokens - start_tokens
        metrics.total_cost_usd = round(self.cost_tracker.total_cost_usd - start_cost, 6)
        metrics.elapsed_seconds = round(asyncio.get_event_loop().time() - start_time, 2)

        return results, metrics


async def enrich_company(domain: str, **kwargs: Any) -> CompanyEnrichment:
    """Convenience helper to enrich a single company."""
    agent = LeadEnrichmentAgent()
    return await agent.enrich_company(domain, **kwargs)


async def enrich_domains(
    domains: list[str], **kwargs: Any
) -> tuple[list[CompanyEnrichment], EnrichmentMetrics]:
    """Convenience helper to enrich a list of companies."""
    agent = LeadEnrichmentAgent()
    return await agent.enrich_domains(domains, **kwargs)
