# Extraction

DAVE supports four extraction modes: zero-config, natural language prompts, Pydantic schemas, and built-in recipes. All modes share the same engine, fetcher routing, cache, retry, rate limit, confidence, and cost tracking infrastructure.

## Zero-config extraction

```python
import dave

page = await dave.extract("https://example.com")
```

Zero-config extraction is designed for first-pass discovery. DAVE infers page type, title, summary, important entities, key facts, links, contact signals, products, prices, jobs, and calls to action.

## Prompt extraction

```python
import dave

result = await dave.extract(
    "https://example.com/pricing",
    "extract each pricing tier with price, billing period, and top features",
)
```

Prompt extraction is useful when you know what you want but do not need a strict Python model yet.

## Schema extraction

```python
from pydantic import BaseModel, Field
import dave

class PricingTier(BaseModel):
    name: str
    price: str | None = None
    billing_period: str | None = None
    features: list[str] = Field(default_factory=list)

class PricingPage(BaseModel):
    tiers: list[PricingTier] = Field(default_factory=list)

pricing = await dave.extract("https://example.com/pricing", PricingPage)
```

Every schema extraction is validated before it is returned. Invalid data raises an exception instead of silently moving bad records into your pipeline.

## Recipes

```python
import dave

company = await dave.recipes.company_info("https://example.com")
pricing = await dave.recipes.pricing("https://example.com/pricing")
jobs = await dave.recipes.job_listings("https://example.com/careers")
```

Recipes return Pydantic models for common workflows.

| Recipe | Output focus |
| --- | --- |
| `company_info` | Name, description, founders, funding, employees, tech stack, social links |
| `pricing` | Pricing tiers, features, limits, calls to action |
| `job_listings` | Open roles, locations, departments, employment type, apply links |
| `contact_info` | Emails, phones, addresses, social links, support links |
| `product_features` | Feature names, descriptions, categories, evidence |
| `reviews` | Testimonials, authors, ratings, sources |

## Metadata

```python
from dave.core.engine import DaveEngine

engine = DaveEngine()
result = await engine.extract("https://example.com", include_metadata=True)
print(result.confidence)
print(result.field_confidence)
print(result.cost_usd)
```

Metadata includes confidence, per-field confidence, evidence snippets, final URL, fetcher name, and cost.

## Streaming

```python
from dave.core.engine import DaveEngine

engine = DaveEngine()
async for event in engine.stream_extract("https://example.com", "get company info"):
    print(event.type, event.message, event.data)
```

Streaming emits fetch start, cost estimate, extraction start, field events, and completion events. It is useful for terminal demos, dashboards, and long pages.
