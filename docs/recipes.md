# DAVE Recipes

Recipes are pre-built extraction flows for common scraping jobs. Each recipe combines a Pydantic schema, a focused prompt, validation, confidence scoring, and CLI support.

## Available recipes

| Recipe | Python call | CLI call |
| --- | --- | --- |
| Company info | `await dave.recipes.company_info(url)` | `dave extract URL --recipe company_info` |
| Pricing | `await dave.recipes.pricing(url)` | `dave extract URL --recipe pricing` |
| Job listings | `await dave.recipes.job_listings(url)` | `dave extract URL --recipe job_listings` |
| Contact info | `await dave.recipes.contact_info(url)` | `dave extract URL --recipe contact_info` |
| Product features | `await dave.recipes.product_features(url)` | `dave extract URL --recipe product_features` |
| Reviews | `await dave.recipes.reviews(url)` | `dave extract URL --recipe reviews` |

## Python usage

```python
import dave

company = await dave.recipes.company_info("https://example.com")
print(company.model_dump())
```

## CLI usage

```bash
dave extract "https://example.com" --recipe company_info
```

## Batch usage

```bash
dave batch urls.txt --recipe pricing --output pricing.json
```

Recipes are intentionally conservative. They should provide useful defaults while still making it easy to switch to custom schemas when your workflow becomes more specific.
