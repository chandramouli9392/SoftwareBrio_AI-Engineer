"""Built-in DAVE extraction recipes.

Recipes are high-signal, typed shortcuts for common developer workflows.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from dave.core.config import DaveConfig


class CompanyInfo(BaseModel):
    """Company intelligence extracted from a page."""

    name: str | None = None
    description: str | None = None
    founders: list[str] = Field(default_factory=list)
    funding: str | None = None
    employees: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    website: str | None = None


class PricingTier(BaseModel):
    """One pricing tier."""

    name: str
    price: str | None = None
    billing_period: str | None = None
    features: list[str] = Field(default_factory=list)


class PricingPage(BaseModel):
    """Pricing page extraction."""

    tiers: list[PricingTier] = Field(default_factory=list)
    free_trial: str | None = None
    enterprise_available: bool | None = None


class JobListing(BaseModel):
    """One job listing."""

    title: str
    location: str | None = None
    department: str | None = None
    employment_type: str | None = None
    url: str | None = None


class JobListings(BaseModel):
    """Open roles on a careers page."""

    jobs: list[JobListing] = Field(default_factory=list)


class ContactInfo(BaseModel):
    """Contact information found on a page."""

    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    social_links: list[str] = Field(default_factory=list)
    contact_forms: list[str] = Field(default_factory=list)


class ProductFeature(BaseModel):
    """One product feature."""

    name: str
    description: str | None = None


class ProductFeatures(BaseModel):
    """Product features found on a page."""

    features: list[ProductFeature] = Field(default_factory=list)


class Review(BaseModel):
    """One review or testimonial."""

    author: str | None = None
    company: str | None = None
    quote: str
    rating: str | None = None


class Reviews(BaseModel):
    """Customer reviews and testimonials."""

    reviews: list[Review] = Field(default_factory=list)


RECIPES: dict[str, tuple[type[BaseModel], str]] = {
    "company_info": (
        CompanyInfo,
        "Extract company intelligence including name, description, founders, funding, employees, tech stack, and website.",
    ),
    "pricing": (
        PricingPage,
        "Extract every pricing tier with price, billing period, included features, free trial details, and enterprise availability.",
    ),
    "job_listings": (
        JobListings,
        "Extract all open positions with title, location, department, employment type, and listing URL.",
    ),
    "contact_info": (
        ContactInfo,
        "Extract emails, phone numbers, social links, and contact form URLs from the page.",
    ),
    "product_features": (
        ProductFeatures,
        "Extract product features with concise descriptions.",
    ),
    "reviews": (
        Reviews,
        "Extract customer reviews, testimonials, authors, companies, and ratings when present.",
    ),
}


def get_recipe(name: str) -> tuple[type[BaseModel], str]:
    """Return the schema and prompt for a built-in recipe."""
    try:
        return RECIPES[name]
    except KeyError as exc:
        known = ", ".join(sorted(RECIPES))
        raise ValueError(f"Unknown recipe {name}. Available recipes: {known}") from exc


async def run_recipe(
    name: str,
    url: str,
    *,
    config: DaveConfig | None = None,
    include_metadata: bool = False,
    **kwargs: Any,
) -> Any:
    """Run a built-in recipe by name."""
    from dave.core.engine import DaveEngine

    schema, prompt = get_recipe(name)
    engine = DaveEngine(config=config)
    return await engine.extract(url, schema, prompt=prompt, include_metadata=include_metadata, **kwargs)


async def company_info(url: str, *, config: DaveConfig | None = None, include_metadata: bool = False, **kwargs: Any) -> Any:
    """Extract company intelligence from a URL."""
    return await run_recipe("company_info", url, config=config, include_metadata=include_metadata, **kwargs)


async def pricing(url: str, *, config: DaveConfig | None = None, include_metadata: bool = False, **kwargs: Any) -> Any:
    """Extract pricing tiers from a URL."""
    return await run_recipe("pricing", url, config=config, include_metadata=include_metadata, **kwargs)


async def job_listings(url: str, *, config: DaveConfig | None = None, include_metadata: bool = False, **kwargs: Any) -> Any:
    """Extract open roles from a URL."""
    return await run_recipe("job_listings", url, config=config, include_metadata=include_metadata, **kwargs)


async def contact_info(url: str, *, config: DaveConfig | None = None, include_metadata: bool = False, **kwargs: Any) -> Any:
    """Extract contact information from a URL."""
    return await run_recipe("contact_info", url, config=config, include_metadata=include_metadata, **kwargs)


async def product_features(url: str, *, config: DaveConfig | None = None, include_metadata: bool = False, **kwargs: Any) -> Any:
    """Extract product features from a URL."""
    return await run_recipe("product_features", url, config=config, include_metadata=include_metadata, **kwargs)


async def reviews(url: str, *, config: DaveConfig | None = None, include_metadata: bool = False, **kwargs: Any) -> Any:
    """Extract reviews and testimonials from a URL."""
    return await run_recipe("reviews", url, config=config, include_metadata=include_metadata, **kwargs)
