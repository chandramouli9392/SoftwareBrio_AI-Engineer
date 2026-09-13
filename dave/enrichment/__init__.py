"""SoftwareBrio Autonomous Lead Enrichment package for DAVE."""

from __future__ import annotations

from dave.enrichment.agent import (
    EnrichmentMetrics,
    LeadEnrichmentAgent,
    enrich_company,
    enrich_domains,
)
from dave.enrichment.cleaner import ContentCleaner, clean_html
from dave.enrichment.discovery import (
    CandidatePage,
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

__all__ = [
    "CandidatePage",
    "CompanyEnrichment",
    "ContactPoint",
    "ContentCleaner",
    "EnrichmentMetrics",
    "EnrichmentStatus",
    "InformationGoal",
    "LeadEnrichmentAgent",
    "LeadershipMember",
    "calculate_confidence_score",
    "clean_html",
    "determine_status",
    "discover_relevant_pages",
    "enrich_company",
    "enrich_domains",
]
