"""Pydantic schemas for SoftwareBrio Autonomous Lead Enrichment."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class EnrichmentStatus(str, Enum):
    """Status of company enrichment process."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ContactPoint(BaseModel):
    """A single verified contact point extracted from company web pages."""

    email: str = Field(description="Generic or business email address discovered on the site.")
    type: str = Field(
        default="generic",
        description="Category of contact point, e.g. generic, sales, support, press, careers.",
    )
    source_url: str = Field(description="The source URL where this contact point was explicitly discovered.")


class LeadershipMember(BaseModel):
    """A leadership or key team member extracted from company pages."""

    name: str = Field(description="Full name of the team member or executive.")
    role: str = Field(description="Official role or title at the company.")
    linkedin_url: str | None = Field(
        default=None,
        description="Explicitly discovered LinkedIn URL for this member, or None if not found.",
    )


class CompanyEnrichment(BaseModel):
    """Structured, evidence-grounded company intelligence output."""

    domain: str = Field(description="Domain of the target company (e.g. postman.com).")
    company_overview: str = Field(
        default="",
        description="Concise, approximately 2-sentence description of what the company does.",
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
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Defensible confidence score from 0.0 to 1.0 reflecting completeness and evidence.",
    )
    source_pages: list[str] = Field(
        default_factory=list,
        description="List of internal URLs visited and analyzed.",
    )
    status: EnrichmentStatus = Field(
        default=EnrichmentStatus.SUCCESS,
        description="Status of the enrichment: success, partial, or failed.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Encountered issues, warnings, or missing data explanations.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: object) -> EnrichmentStatus:
        """Coerce strings to EnrichmentStatus enum safely."""
        if isinstance(v, EnrichmentStatus):
            return v
        if isinstance(v, str):
            clean_v = v.strip().lower()
            for status in EnrichmentStatus:
                if status.value == clean_v:
                    return status
        return EnrichmentStatus.SUCCESS

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Ensure confidence score is strictly clamped between 0.0 and 1.0."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {v}")
        return round(v, 3)
