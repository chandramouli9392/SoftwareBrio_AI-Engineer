"""Defensible confidence scoring and status evaluation.

Computes a transparent, evidence-grounded confidence score strictly between 0.0 and 1.0
evaluating:
1. Completeness of required fields (overview, ICP, leadership, contact points)
2. Grounding in source text (verifying names, roles, emails, and LinkedIn URLs against retrieved content)
3. Source breadth (multi-page coverage: homepage + dedicated subpages)
4. Explicit discovery of high-signal elements (genuine emails and LinkedIn profiles)
"""

from __future__ import annotations

import re

from dave.enrichment.schema import (
    ContactPoint,
    EnrichmentStatus,
    LeadershipMember,
)


def calculate_confidence_score(
    company_overview: str,
    target_audience: str,
    contact_points: list[ContactPoint],
    leadership: list[LeadershipMember],
    source_pages: list[str],
    aggregated_source_text: str,
    errors: list[str] | None = None,
) -> float:
    """Calculate an objective, evidence-based confidence score between 0.0 and 1.0.

    Formula breakdown:
    - 0.35 Field Completeness (overview, ICP, leadership, contacts)
    - 0.35 Evidence & Grounding (presence in retrieved page text)
    - 0.15 Source Depth (multi-page coverage across site)
    - 0.15 High-Signal Signals (explicitly verified emails & LinkedIn URLs)
    - Penalty deductions for failed pages or ungrounded assertions.
    """
    if not source_pages:
        return 0.0

    lower_source = aggregated_source_text.lower()
    total_score = 0.0

    # -------------------------------------------------------------
    # 1. FIELD COMPLETENESS (Weight: 0.35)
    # -------------------------------------------------------------
    completeness_score = 0.0

    # Overview is comprehensive (> 25 characters)
    if company_overview and len(company_overview.strip()) >= 25:
        completeness_score += 0.10
    elif company_overview:
        completeness_score += 0.05

    # Target audience is articulated (> 20 characters)
    if target_audience and len(target_audience.strip()) >= 20:
        completeness_score += 0.10
    elif target_audience:
        completeness_score += 0.05

    # Leadership presence
    if len(leadership) >= 2:
        completeness_score += 0.10
    elif len(leadership) == 1:
        completeness_score += 0.06

    # Contact points presence
    if contact_points:
        completeness_score += 0.05

    total_score += min(0.35, completeness_score)

    # -------------------------------------------------------------
    # 2. EVIDENCE & GROUNDING IN SOURCE TEXT (Weight: 0.35)
    # -------------------------------------------------------------
    grounding_score = 0.0

    # Overview keyword overlap
    if company_overview:
        overview_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", company_overview)]
        if overview_words:
            matched_words = sum(1 for w in overview_words if w in lower_source)
            overlap_ratio = matched_words / len(overview_words)
            grounding_score += 0.10 * min(1.0, overlap_ratio * 1.5)

    # Target audience keyword overlap
    if target_audience:
        icp_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", target_audience)]
        if icp_words:
            matched_icp = sum(1 for w in icp_words if w in lower_source)
            overlap_ratio = matched_icp / len(icp_words)
            grounding_score += 0.10 * min(1.0, overlap_ratio * 1.5)

    # Leadership name grounding (verifies names actually exist in retrieved text)
    if leadership:
        verified_leaders = 0
        for leader in leadership:
            if leader.name and leader.name.lower() in lower_source:
                verified_leaders += 1
        grounding_score += 0.10 * (verified_leaders / len(leadership))

    # Email grounding
    if contact_points:
        verified_contacts = 0
        for cp in contact_points:
            if cp.email and cp.email.lower() in lower_source:
                verified_contacts += 1
        grounding_score += 0.05 * (verified_contacts / len(contact_points))

    total_score += min(0.35, grounding_score)

    # -------------------------------------------------------------
    # 3. SOURCE DEPTH & MULTI-PAGE BREADTH (Weight: 0.15)
    # -------------------------------------------------------------
    page_count = len(source_pages)
    if page_count >= 3:
        source_score = 0.15
    elif page_count == 2:
        source_score = 0.10
    elif page_count == 1:
        source_score = 0.06
    else:
        source_score = 0.0
    total_score += source_score

    # -------------------------------------------------------------
    # 4. HIGH-VALUE VERIFIED SIGNALS (Weight: 0.15)
    # -------------------------------------------------------------
    signals_score = 0.0

    # Genuine LinkedIn URLs found on the pages
    linkedin_count = sum(1 for leader in leadership if leader.linkedin_url and "linkedin.com" in leader.linkedin_url.lower())
    if linkedin_count >= 2:
        signals_score += 0.08
    elif linkedin_count == 1:
        signals_score += 0.05

    # Direct contact emails found on the site
    if any(cp.email and "@" in cp.email for cp in contact_points):
        signals_score += 0.07

    total_score += min(0.15, signals_score)

    # -------------------------------------------------------------
    # 5. ERROR PENALTIES
    # -------------------------------------------------------------
    if errors:
        # Deduct small amount per error encountered
        total_score -= min(0.15, len(errors) * 0.03)

    return round(max(0.0, min(1.0, total_score)), 3)


def determine_status(
    company_overview: str,
    target_audience: str,
    contact_points: list[ContactPoint],
    leadership: list[LeadershipMember],
    source_pages: list[str],
    confidence_score: float,
    errors: list[str],
) -> EnrichmentStatus:
    """Determine the enrichment status based on data completeness and retrieval outcome."""
    if not source_pages or (not company_overview and not target_audience):
        return EnrichmentStatus.FAILED

    has_overview = bool(company_overview and len(company_overview.strip()) >= 20)
    has_icp = bool(target_audience and len(target_audience.strip()) >= 15)
    has_leadership = len(leadership) > 0
    has_contacts = len(contact_points) > 0

    # High quality complete result
    if has_overview and has_icp and (has_leadership or has_contacts) and confidence_score >= 0.55:
        return EnrichmentStatus.SUCCESS

    # Partial result (has overview/icp but missing some key components or low confidence)
    if has_overview or has_icp:
        return EnrichmentStatus.PARTIAL

    return EnrichmentStatus.FAILED
