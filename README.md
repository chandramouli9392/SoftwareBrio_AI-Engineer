<p align="center">
  <h1 align="center">BrioLeadEnricher</h1>
</p>

<p align="center">
  <strong>AI-powered scraping without LangChain, graph DSLs, or dependency bloat.</strong>
</p>

<p align="center">
  Give DAVE a URL and get clean, validated, structured data. DAVE ships with five runtime dependencies, no LangChain dependency, and no graph framework to learn. Use a prompt, a Pydantic schema, a built-in recipe, or nothing at all.
</p>

<p align="center">
  <a href="https://github.com/workwithlos-ui/dave/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/workwithlos-ui/dave/ci.yml?branch=main&label=tests" alt="Tests"></a>
  <a href="https://pypi.org/project/dave-ai/"><img src="https://img.shields.io/pypi/v/dave-ai?label=pypi" alt="PyPI"></a>
  <a href="https://pypi.org/project/dave-ai/"><img src="https://img.shields.io/pypi/pyversions/dave-ai" alt="Python versions"></a>
  <a href="https://pypi.org/project/dave-ai/"><img src="https://img.shields.io/pypi/dm/dave-ai?label=downloads" alt="Downloads"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/workwithlos-ui/dave" alt="License"></a>
</p>

---

## Try it in 10 seconds

```bash
pip install dave-ai
dave extract "https://openai.com" --recipe company_info
```

Or use the library in one line:

```python
import dave

result = await dave.extract("https://competitor.com")
```

That call has no prompt and no schema. DAVE still returns intelligent structured data by detecting the page type, important entities, key facts, calls to action, prices, contact signals, and links. This is the zero-config path for demos, exploration, and first-pass research.

## The 3-line version

```python
import dave

result = await dave.extract("https://example.com", "get the title and description")
print(result)
```

DAVE is designed for developers who need more than a prototype but do not want a full LangChain dependency tree. It combines fetcher selection, LLM extraction, Pydantic validation, caching, retries, rate limits, heuristic confidence scoring, cost tracking, batch jobs, and a plugin system in one typed Python package with only five runtime dependencies.

## Why DAVE?

Most AI scraping tools are impressive in a notebook and fragile in a production job — heavy dependency stacks, no retries, no caching, no cost visibility. DAVE takes the opposite path: a small typed core, direct fetcher and extractor interfaces, and production controls that are easy to reason about.

| What developers need | How DAVE handles it |
| --- | --- |
| Keep dependency risk low | Ships with five runtime dependencies: Beautiful Soup, HTTPX, Pydantic, Rich, and Typer |
| Avoid framework lock-in | Uses no LangChain dependency and no graph DSL |
| Scrape static and JavaScript-heavy pages | Auto-selects HTTP or Playwright, with extension points for external crawlers |
| Extract with a prompt or a schema | Accepts natural language prompts, Pydantic models, built-in recipes, or no prompt at all |
| Trust the output | Validates schema extraction through Pydantic and reports transparent heuristic confidence |
| Keep costs visible | Estimates tokens before runs and tracks cost after runs |
| Run hundreds of URLs | Includes batch mode, retries, rate limits, progress, and JSON output |
| Avoid building glue code | Ships caching, queueing, structured logging, CLI commands, and plugin registration |

Confidence is a transparent heuristic based on evidence presence and source-text overlap, not a model-reported probability.

## Zero-config magic

DAVE can run with no prompt and no schema:

```python
import dave

page = await dave.extract("https://stripe.com")
```

A typical result looks like this:

```json
{
  "page_type": "company_or_content",
  "title": "Stripe",
  "summary": "Financial infrastructure for the internet",
  "key_entities": ["Stripe", "Payments", "Billing"],
  "key_facts": ["Stripe builds programmable financial services for businesses."],
  "links": ["https://stripe.com/pricing"],
  "contacts": {"emails": [], "phones": []},
  "prices": [],
  "products": ["Payments", "Billing", "Connect"],
  "jobs": [],
  "calls_to_action": ["Start now", "Contact sales"]
}
```

Zero-config extraction is not a replacement for schemas in critical workflows. It is the fastest way to inspect a new page, build lead lists, prototype competitive intelligence, and discover what schema you should use next.

## Recipes that work out of the box

DAVE recipes are typed extraction flows for the web pages developers scrape every week.

| Recipe | Python | CLI |
| --- | --- | --- |
| Company info | `await dave.recipes.company_info(url)` | `dave extract URL --recipe company_info` |
| Pricing tiers | `await dave.recipes.pricing(url)` | `dave extract URL --recipe pricing` |
| Job listings | `await dave.recipes.job_listings(url)` | `dave extract URL --recipe job_listings` |
| Contact info | `await dave.recipes.contact_info(url)` | `dave extract URL --recipe contact_info` |
| Product features | `await dave.recipes.product_features(url)` | `dave extract URL --recipe product_features` |
| Reviews and testimonials | `await dave.recipes.reviews(url)` | `dave extract URL --recipe reviews` |

Example:

```python
import dave

company = await dave.recipes.company_info("https://linear.app")
pricing = await dave.recipes.pricing("https://linear.app/pricing")
```

The returned objects are Pydantic models, so they are easy to validate, serialize, and pass into downstream systems.

## Beautiful CLI output

DAVE is built to look good in the terminal because the terminal is where scraping jobs fail, recover, and prove they are working.

```text
$ dave extract "https://openai.com" --recipe company_info

╭──────────── Cost estimate ────────────╮
│ This extraction will use about        │
│ 2,000 tokens for roughly $0.003000.   │
╰───────────────────────────────────────╯
Proceed? [Y/n] y

╭──── Data Acquisition and Validation Engine ────╮
│ DAVE is extracting structured data              │
╰────────────────────────────────────────────────╯
+ Fetching page with auto fetcher 0:00:01
field name = OpenAI
field description = AI research and deployment company
field tech_stack = ["Python", "Kubernetes", "LLM APIs"]
field social_links = ["https://twitter.com/openai"]

╭────────────────── DAVE Extraction: company_info ──────────────────╮
│ Field        │ Value                                               │
│ name         │ OpenAI                                              │
│ description  │ AI research and deployment company                  │
│ founders     │ []                                                  │
│ funding      │ null                                                │
│ employees    │ null                                                │
│ tech_stack   │ ["Python", "Kubernetes", "LLM APIs"]              │
╰───────────────────────────────────────────────────────────────────╯

Run Metadata
confidence  0.91
cost_usd    0.003
fetcher     playwright
final_url   https://openai.com
```

Use machine-readable output when you need it:

```bash
dave extract "https://example.com" --prompt "get the title" --output json
```

## Search the web, then extract

Skip the step where you go find URLs yourself. Give DAVE a query and it searches the web, then runs the normal extraction pipeline over each result.

```bash
dave search "best open source CRM" --recipe company_info --limit 5
```

```python
import dave

report = await dave.search_extract("best open source CRM", prompt="get the company name and pricing", limit=5)
for item in report.ok_items:
    print(item.hit.url, item.data)
```

Search providers are pluggable so the core stays dependency-light. The default uses DuckDuckGo's HTML endpoint over the HTTPX and Beautiful Soup that DAVE already ships, so there is no API key and no extra dependency. Register your own provider for an internal search index or a paid search API:

```python
from dave.plugins import register_search
from dave.search.base import BaseSearchProvider, SearchHit

class InternalSearch(BaseSearchProvider):
    name = "internal"

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        return [SearchHit(url="https://intranet.example/doc/1", title="Doc 1", rank=1)]

register_search("internal", InternalSearch())
```

```bash
dave search "quarterly targets" --search-provider internal --recipe company_info
```

Per-result failures are isolated: a URL that fails to fetch or extract is reported with its error while the rest of the batch continues.

## Local business leads

Turn an industry and a city into a ready-to-dial list — real businesses with phone numbers, addresses, ratings, and websites. Backed by the Apify Google Maps scraper, the reliable source for local-business data that general web scraping can't get.

```bash
export APIFY_API_KEY=...        # from console.apify.com/account/integrations
dave leads "roofing companies" "Dallas, TX" --max 20 --output csv > leads.csv
```

```python
import dave

report = await dave.find_leads("med spas", "Scottsdale, AZ", max_results=25)
for lead in report.leads:
    print(lead.business_name, lead.phone, lead.website)
print(report.to_csv())   # Business Name, Phone, Website, Address, Category, Rating, Reviews, Call Summary, Status
```

Only businesses with a phone are returned (it's built for cold calling). Pair it with DAVE's extraction to enrich each business's own site, or with an LLM to write per-lead call summaries. This is the discovery layer general AI scrapers don't have.

## Vision: structured data from images

When the DOM lies — canvas-rendered apps, image-only pages, scanned documents, screenshots, invoices — extract from the pixels instead. DAVE sends the image to a vision-capable model (OpenAI, Anthropic, or Gemini) and returns the same validated, confidence-scored structured data the text pipeline produces.

```python
import dave
from pydantic import BaseModel

class Invoice(BaseModel):
    vendor: str
    total: str

invoice = await dave.extract_image("invoice.png", Invoice)
print(invoice.vendor, invoice.total)
```

Pass a file path or raw bytes. Image extraction has no source text to ground against, so confidence reflects field completeness and is labelled honestly rather than faked as source overlap.

## Crawl a whole site

Point DAVE at a starting URL and it follows links across the site, extracting from every page. Breadth-first, bounded by page count and depth, same-domain by default. Every page goes through the full pipeline — cache, retries, rate limits, robots.txt, and confidence all apply per page.

```bash
dave crawl "https://example.com" --recipe company_info --max-pages 20 --max-depth 2
```

```python
import dave

report = await dave.crawl("https://example.com", "get the page title and summary", max_pages=20, max_depth=2)
for page in report.ok_items:
    print(page.url, page.data)
```

A page that fails to fetch or extract is recorded with its error; the crawl keeps going. Use `--any-domain` to follow external links.

## Batch mode

Process hundreds of known URLs with progress, retries, cache hits, and a cost summary.

```bash
dave batch urls.txt --recipe pricing --output results.json
```

The input file is plain text:

```text
https://example.com/pricing
https://another-example.com/pricing
https://vendor.example/pricing
```

DAVE writes a JSON array with one item per URL. Failed URLs include the error message and successful URLs include data, confidence, evidence, cost, final URL, and fetcher metadata.

## Cost calculator

DAVE estimates token usage before running an extraction.

```text
This extraction will use about 2,000 tokens for roughly $0.003000.
Proceed? [Y/n]
```

The estimate uses the selected model, prompt, schema, and fetched page text. After extraction, DAVE returns tracked usage and cost metadata so teams can monitor spending by job, domain, recipe, or customer.

## Streaming extraction

When `--stream` is enabled, DAVE emits field events as data is found instead of waiting until the full extraction is complete.

```python
from dave.core.engine import DaveEngine

engine = DaveEngine()

async for event in engine.stream_extract("https://example.com", "get title and pricing"):
    print(event.type, event.message, event.data)
```

Streaming is useful for long pages, operator dashboards, live demos, and batch jobs where early partial output is better than silence.

## Pydantic-first extraction

```python
from pydantic import BaseModel, Field
import dave

class PricingTier(BaseModel):
    name: str
    price: str | None = None
    features: list[str] = Field(default_factory=list)

class PricingPage(BaseModel):
    tiers: list[PricingTier] = Field(default_factory=list)

pricing = await dave.extract("https://vendor.example/pricing", PricingPage)
print(pricing.model_dump())
```

Every schema extraction is validated before it is returned. If a provider returns invalid JSON or mismatched data, DAVE fails loudly instead of silently contaminating your pipeline.

## Architecture

```mermaid
flowchart LR
    A[URL plus prompt, schema, recipe, or zero-config] --> B[DAVE Engine]
    B --> C{Fetcher Router}
    C --> D[HTTP Fetcher]
    C --> E[Playwright Fetcher]
    C --> F[Firecrawl or Crawl4AI Plugin]
    D --> G[Cache and Rate Limiter]
    E --> G
    F --> G
    G --> H[Chunker]
    H --> I{LLM Provider}
    I --> J[OpenAI]
    I --> K[Anthropic]
    I --> L[Ollama]
    H --> M[Pydantic Validator]
    J --> M
    K --> M
    L --> M
    M --> N[Confidence Scoring]
    N --> O[Structured Data]
    O --> P[CLI, Python API, Batch Jobs]
```

## Fetchers

DAVE ships with a multi-fetcher backend and a simple routing model.

| Fetcher | Use it for | Command |
| --- | --- | --- |
| `auto` | Let DAVE choose based on page signals | `--fetcher auto` |
| `http` | Fast static pages and APIs | `--fetcher http` |
| `playwright` | JavaScript-rendered pages | `--fetcher playwright` |
| `stealth` | Sites that block ordinary automation | `--fetcher stealth` |
| `file` | Local files: text, HTML, Markdown, JSON, PDF | auto for local paths and `file://` |
| plugin | Firecrawl, Crawl4AI, internal crawlers, or custom fetchers | `--fetcher your_name` |

Proxy rotation is configured through `DaveConfig.proxies`. Bring your own proxy URLs and DAVE will rotate them across requests.

### Respecting robots.txt

Set `respect_robots_txt=True` (or `DaveConfig(respect_robots_txt=True)`) and DAVE checks each site's robots.txt before fetching, caches the result per domain, and refuses disallowed URLs with a clear `RobotsDisallowedError`. If robots.txt is unreachable, DAVE allows the fetch. Local files are never subject to robots rules.

### Stealth fetcher

Some sites block headless browsers with bot walls and 403s. The stealth fetcher runs Playwright with an evasion layer — automation-control launch flags, a realistic browser context and client hints, and an init script that hides the signals most bot walls inspect (`navigator.webdriver`, missing `window.chrome`, headless WebGL vendor strings). It adds no heavy dependency such as `undetected-playwright`; it only needs Playwright, installed through the `stealth` extra.

```bash
pip install "dave-ai[stealth]"
python -m playwright install chromium
dave search "best open source CRM" --recipe company_info --fetcher stealth
```

```python
import dave
from dave.core.config import DaveConfig
from dave.fetchers.stealth import register_stealth_fetcher

register_stealth_fetcher()
result = await dave.extract("https://example.com", "get the title", config=DaveConfig(fetcher="stealth"))
```

Stealth reduces detection; it is not a guarantee. Pair it with `DaveConfig.proxies` for sites that rate-limit or block by IP. Use it where you have permission to scrape, and respect each site's terms of service and `robots.txt`.

## Plugin system

DAVE is designed for community extensions. Register custom fetchers and extractors without forking the project.

```python
from dave.plugins import register_fetcher
from dave.fetchers.base import Fetcher, FetchResult

class InternalFetcher(Fetcher):
    name = "internal"

    async def fetch(self, url: str) -> FetchResult:
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content="<html><title>Internal</title></html>",
            content_type="text/html",
            elapsed_ms=12.0,
            rendered=False,
        )

register_fetcher("internal", InternalFetcher)
```

```bash
dave extract "https://internal.example" --fetcher internal --prompt "summarize this page"
```

Plugins make it possible to add authenticated browser sessions, enterprise crawlers, proxy vendors, custom LLM routers, domain-specific validators, and private data enrichment steps.

## Benchmarks coming

A reproducible benchmark suite is in development. We will publish real numbers, not targets, once it lands. Track it in issue #1.

The benchmark suite will measure end-to-end extraction from real product, pricing, jobs, documentation, and contact pages. It will publish fixtures, scripts, provider settings, hardware assumptions, network assumptions, and raw results so maintainers and users can reproduce the numbers.

## Configuration

```python
from dave.core.config import DaveConfig, LLMConfig

config = DaveConfig(
    fetcher="auto",
    llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
    cache_path=".dave/cache.sqlite3",
    rate_limit_per_domain=2.0,
    proxies=["http://user:pass@proxy.example:8080"],
)
```

Environment variables are supported for common provider keys:

| Variable | Purpose |
| --- | --- |
| `DAVE_LLM_PROVIDER` | Select `openai`, `anthropic`, `gemini`, `groq`, `mistral`, `ollama`, or `mock` |
| `DAVE_LLM_API_KEY` | Provider API key (used by any provider) |
| `OPENAI_API_KEY` | OpenAI fallback key |
| `ANTHROPIC_API_KEY` | Anthropic fallback key |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Gemini fallback key |
| `GROQ_API_KEY` | Groq fallback key |
| `MISTRAL_API_KEY` | Mistral fallback key |
| `DAVE_LLM_MODEL` | Model override |

All cloud providers run over plain HTTPX with native request shapes — no LangChain, no provider SDKs. OpenAI, Groq, and Mistral share the OpenAI-compatible chat API; Gemini and Anthropic use their native endpoints; Ollama runs locally.

## SoftwareBrio Autonomous Lead Enrichment Agent

This project is submitted for the **SoftwareBrio AI Engineer Intern Practical Take-Home Assignment**.

### Problem statement

Given a list of company domains, autonomously retrieve public web content and produce structured, evidence-grounded company intelligence without human input. The pipeline must handle SPA pages, missing data, API rate limits, and unreachable domains gracefully.

### How DAVE is reused

The SoftwareBrio agent is built entirely on top of DAVE's production-grade engine:

- **DaveEngine** handles HTTP fetching, Playwright JS rendering, caching, rate limiting, and retries
- **LLMExtractor** handles multi-provider LLM calls with chunking, retries, and cost tracking
- **ContentCleaner** converts raw HTML into clean Markdown text for the LLM
- **CostTracker** tracks per-run token and cost usage

### End-to-end pipeline

```
Input domains (data/input.json)
  → Domain normalization
  → Homepage fetch (HTTP or Playwright auto-selected)
  → HTML cleaning → clean Markdown text
  → Goal-driven page discovery (contact, leadership, ICP pages prioritized)
  → Subpage fetching (up to max_pages per domain)
  → Context aggregation (homepage + subpages)
  → LLM structured extraction (CompanyExtractionPayload via Pydantic)
  → Programmatic evidence verification (emails, LinkedIn URLs checked against retrieved text)
  → Markdown sanitization (no raw Markdown syntax in output)
  → Confidence scoring (completeness + grounding + source depth + signal quality)
  → Status determination (success / partial / failed)
  → JSON output (data/output.json)
```

### Installation and setup

```bash
git clone https://github.com/workwithlos-ui/dave.git
cd dave
python -m pip install -e ".[dev]"
```

For JavaScript-heavy sites:

```bash
python -m pip install -e ".[playwright]"
python -m playwright install chromium
```

### Environment variables

Copy `.env.example` to `.env` and fill in your API key. **Never commit `.env`.**

```bash
cp .env.example .env
# Edit .env and set your provider key, e.g.:
# DAVE_LLM_PROVIDER=groq
# DAVE_LLM_MODEL=openai/gpt-oss-20b
# GROQ_API_KEY=<your-key>
```

| Variable | Purpose |
| --- | --- |
| `DAVE_LLM_PROVIDER` | LLM provider: `openai`, `anthropic`, `gemini`, `groq`, `mistral`, `ollama`, `mock` |
| `DAVE_LLM_MODEL` | Model name (must match provider) |
| `DAVE_LLM_API_KEY` | Generic API key (any provider) |
| `GROQ_API_KEY` | Groq-specific key |
| `OPENAI_API_KEY` | OpenAI-specific key |
| `ANTHROPIC_API_KEY` | Anthropic-specific key |
| `GEMINI_API_KEY` | Gemini-specific key |

### How to run the agent

```bash
# Default: reads data/input.json, writes data/output.json
dave enrich --provider groq --model openai/gpt-oss-20b --input data/input.json --output data/output.json

# With a different provider
dave enrich --provider openai --model gpt-4o-mini --input data/input.json --output data/output.json

# Mock run (no API key required, for local testing)
dave enrich --provider mock --model mock --input data/input.json --output data/output.json
```

### Example input (`data/input.json`)

```json
[
  "postman.com",
  "supabase.com",
  "vapi.ai"
]
```

### Output schema

Each entry in `data/output.json` conforms to `CompanyEnrichment`:

| Field | Type | Description |
| --- | --- | --- |
| `domain` | `str` | Normalized company domain |
| `company_overview` | `str` | Two-sentence factual summary from evidence |
| `target_audience` | `str` | ICP derived from product/pricing/customer pages |
| `contact_points` | `list[ContactPoint]` | Verified public email addresses with source URL |
| `leadership` | `list[LeadershipMember]` | Names, roles, and verified LinkedIn URLs |
| `confidence_score` | `float` | Evidence-grounded score from `0.0` to `1.0` |
| `source_pages` | `list[str]` | All pages fetched and analyzed |
| `status` | `str` | `success`, `partial`, or `failed` |
| `errors` | `list[str]` | Warnings and non-fatal failures recorded |

### Anti-hallucination safeguards

- Contact emails must appear in retrieved source text to be included
- LinkedIn URLs must appear in retrieved source text to be included
- The LLM system prompt explicitly forbids fabrication
- Markdown link syntax is stripped from all text fields before output
- Fallback text is sourced from actual page content, not generated

### Error handling and resilience

- Per-domain failure isolation: one domain failing does not stop the batch
- Homepage fetch failure: returns `status=failed` with error recorded
- Subpage 404: logged as warning, enrichment continues with available data
- LLM rate limit: automatic retry with parsed `Retry-After` wait time
- LLM failure: recorded in `errors`, fallback extraction from raw text attempted
- Invalid domain: `status=failed`, other domains unaffected
- All errors surfaced in the `errors` field of the JSON output

### Evidence verification and confidence scoring

The confidence score is computed from four objective dimensions:

| Dimension | Weight | Signal |
| --- | --- | --- |
| Field completeness | 35% | Overview, ICP, leadership, contacts present |
| Evidence grounding | 35% | Keywords from overview/ICP/names found in source text |
| Source depth | 15% | Multiple pages fetched (homepage + subpages) |
| High-value signals | 15% | Verified emails and LinkedIn URLs on the pages |

Errors deduct up to 0.15 from the final score.

### Testing

```bash
# Full test suite
python -m pytest tests/ -v

# Lint
python -m ruff check dave/ tests/

# Mock enrichment run (no API key needed)
dave enrich --provider mock --model mock --input data/input.json --output data/output.json
```

### Security note

`.env` is listed in `.gitignore` and is **never committed**. The `.env.example` file contains only placeholder values. No API key is hard-coded anywhere in the source code, tests, README, or generated output.

---


## Local development

```bash
git clone https://github.com/workwithlos-ui/dave.git
cd dave
python -m pip install -e ".[dev]"
pytest
ruff check .
```


Install Playwright support when you want JavaScript rendering:

```bash
python -m pip install -e ".[playwright]"
python -m playwright install chromium
```

The stealth fetcher uses the same Playwright runtime, available through the `stealth` extra:

```bash
python -m pip install -e ".[stealth]"
python -m playwright install chromium
```

## Project structure

```text
dave/
  core/          Engine, config, retries, queue, rate limits
  fetchers/      HTTP, Playwright, stealth, Firecrawl, Crawl4AI, router
  search/        Web search providers (DuckDuckGo, mock, pluggable)
  extractors/    LLM extraction, schema validation, confidence
  antibot/       Proxy and user-agent helpers
  cache/         SQLite response cache
  monitoring/    Cost tracking and structured logging
  cli/           Rich and Typer command line interface
  plugins.py     Community extension registry
  recipes.py     Built-in extraction recipes
```

## Roadmap

| Milestone | Status |
| --- | --- |
| Zero-config extraction | Done |
| Built-in recipes | Done |
| Streaming CLI output | Done |
| Batch mode | Done |
| Plugin registry | Done |
| Search plus extraction | Done |
| Stealth fetcher plugin | Done |
| Semantic chunking | Done |
| Native multi-provider (OpenAI, Anthropic, Gemini, Groq, Mistral, Ollama) | Done |
| Local file and PDF input | Done |
| robots.txt politeness | Done |
| Vision: structured data from images | Done |
| Multi-page crawling | Done |
| Local business leads (Apify Google Maps) | Done |
| Hosted benchmark dashboard | Planned |
| More recipe packs | Planned |
| OpenTelemetry traces | Planned |

## Contributing

DAVE is built for developers who scrape in production. Contributions should improve reliability, ergonomics, tests, documentation, or real-world extraction quality.

Before opening a pull request, please run:

```bash
pytest
ruff check .
python -m compileall dave
```

Good first contributions include new recipes, fetcher plugins, provider adapters, benchmark cases, docs examples, and domain-specific validators. Please keep code typed, keep tests meaningful, and do not add em dash characters to any file.

## License

DAVE is released under the MIT License. See [LICENSE](LICENSE).
