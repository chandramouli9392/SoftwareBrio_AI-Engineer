# ⚡ BrioLeadEnricher

## 🤖 Autonomous Lead Enrichment Agent

> **Turn company domains into verified, structured lead intelligence — autonomously.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Pydantic](https://img.shields.io/badge/Structured%20Output-Pydantic-E92063)](https://docs.pydantic.dev/)
[![Playwright](https://img.shields.io/badge/Browser-Playwright-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![LLM](https://img.shields.io/badge/LLM-Groq%20%7C%20OpenAI%20%7C%20Gemini-8B5CF6)](#llm-providers)
[![Tests](https://img.shields.io/badge/Tests-96%20Passed-success)](#testing)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](#license)

**SoftwareBrio AI Engineer Intern — Practical Take-Home Assignment**

BrioLeadEnricher is an autonomous web intelligence pipeline that accepts a list of company domains and transforms public web content into **structured, evidence-grounded company intelligence**.

It autonomously discovers relevant pages, handles JavaScript-rendered websites, cleans webpage content, extracts structured information with an LLM, verifies extracted evidence programmatically, calculates confidence, isolates failures, and produces machine-readable JSON.

---

# ✨ What It Does

```text
                         ┌───────────────────────┐
                         │   🌐 COMPANY DOMAIN   │
                         │      postman.com       │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   🔎 AUTONOMOUS       │
                         │      DISCOVERY        │
                         │                       │
                         │  About • Team • Sales │
                         │  Contact • Pricing    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   🕷️ SMART BROWSING   │
                         │                       │
                         │   HTTP / Playwright   │
                         │   Retries / Caching   │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   🧹 CONTENT CLEANER  │
                         │                       │
                         │ HTML → Clean Text    │
                         │ Remove JS / CSS / SVG │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   🧠 STRUCTURED LLM   │
                         │       EXTRACTION     │
                         │                       │
                         │ Company • ICP • Email │
                         │ Leadership • LinkedIn│
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   🛡️ EVIDENCE CHECK   │
                         │                       │
                         │ "Does the source     │
                         │  actually support it?"│
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   📊 CONFIDENCE       │
                         │       SCORING         │
                         │                       │
                         │ Completeness          │
                         │ Grounding             │
                         │ Source Depth          │
                         │ High-value Signals    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   📦 STRUCTURED JSON  │
                         │                       │
                         │  data/output.json     │
                         └───────────────────────┘

# Key Features

### Autonomous Website Enrichment

The agent receives only company domains and determines which pages are useful for enrichment.

It prioritizes pages related to:

* About
* Company
* Team
* Leadership
* Contact
* Sales
* Pricing
* Enterprise
* Customers
* Solutions

### JavaScript-Aware Browsing

The underlying DAVE engine supports:

* HTTP fetching
* Playwright rendering
* Automatic fetcher selection
* Stealth fetching
* Retry handling
* Rate limiting
* Caching

This allows the agent to work with both traditional static websites and JavaScript-heavy pages.

### Clean Content Before LLM Processing

Raw HTML is never directly passed to the LLM.

The pipeline converts webpage content into a cleaner intermediate representation:

```text
Raw HTML
   ↓
DOM parsing
   ↓
Remove scripts
   ↓
Remove styles
   ↓
Remove SVG/boilerplate
   ↓
Extract meaningful text
   ↓
Clean Markdown/text
   ↓
LLM
```

This reduces unnecessary tokens and makes extraction more reliable.

Markdown is used as an intermediate representation. Final structured fields are sanitized before being written to the output.

### Structured LLM Extraction

The LLM is constrained by a Pydantic schema.

The primary output contains:

* Company overview
* Target audience / ICP
* Public generic email addresses
* Leadership/team members
* Roles
* LinkedIn URLs when discoverable
* Confidence score
* Source pages
* Processing status
* Errors

This prevents the application from depending on free-form LLM responses.

### Evidence Verification

The LLM output is not blindly trusted.

Extracted contact information and LinkedIn URLs are checked against retrieved webpage evidence before being included in the final output.

```text
LLM proposes information
        ↓
Search retrieved evidence
        ↓
Information exists in source?
      /       \
    YES        NO
     ↓          ↓
Include       Reject
```

### Confidence Scoring

The final confidence score is calculated from objective signals rather than simply trusting a model-generated probability.

The scoring system considers:

| Dimension          | Weight |
| ------------------ | -----: |
| Field completeness |    35% |
| Evidence grounding |    35% |
| Source depth       |    15% |
| High-value signals |    15% |

Errors can reduce the final score.

This makes the confidence value more interpretable for downstream lead-processing workflows.

### Failure Isolation

A failure for one company does not stop the complete batch.

```text
postman.com
    ↓
SUCCESS

supabase.com
    ↓
SUCCESS

invalid-domain.example
    ↓
FAILED

vapi.ai
    ↓
SUCCESS
```

The invalid domain is recorded in the output while the remaining companies continue processing.

---

# Demonstrated Run

The implementation was tested against the required assignment domains:

```text
postman.com
supabase.com
vapi.ai
```

Command used:

```bash
dave enrich \
  --provider groq \
  --model openai/gpt-oss-20b \
  --input data/input.json \
  --output data/output.json
```

## Results

| Company      | Status  | Confidence | Pages | Contacts | Leaders |
| ------------ | ------- | ---------: | ----: | -------: | ------: |
| postman.com  | success |       0.92 |     5 |        3 |       3 |
| supabase.com | success |       0.92 |     5 |        5 |       2 |
| vapi.ai      | success |       0.71 |     5 |        0 |       1 |

### Batch Summary

```text
Companies processed: 3
Successful:          3
Partial:             0
Failed:              0

Pages analyzed:      15
Tokens used:         52,440
Estimated cost:      $0.071274
```

The complete structured result is written to:

```text
data/output.json
```

---

# Architecture

```text
                    ┌──────────────────────┐
                    │   data/input.json    │
                    │  Company Domains     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Domain Normalization │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Homepage Fetch     │
                    │ HTTP / Playwright    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Content Cleaner    │
                    │ HTML → Clean Text    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Relevant Page        │
                    │ Discovery            │
                    └──────────┬───────────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
              /about       /contact      /pricing
                  │            │            │
                  └────────────┼────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Context Aggregation  │
                    │ Homepage + Subpages  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Structured LLM       │
                    │ Extraction           │
                    │ Pydantic Schema      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Evidence Verification│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Markdown Sanitization│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Confidence Scoring   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Status Determination │
                    │ success / partial /  │
                    │ failed               │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  data/output.json    │
                    └──────────────────────┘
```

---

# Project Structure

```text
BrioLeadEnricher/
│
├── dave/
│   │
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── cleaner.py
│   │   ├── discovery.py
│   │   ├── schema.py
│   │   └── scorer.py
│   │
│   ├── core/
│   │   ├── engine.py
│   │   ├── config.py
│   │   ├── retries.py
│   │   ├── queue.py
│   │   └── rate_limit.py
│   │
│   ├── fetchers/
│   │   ├── http.py
│   │   ├── playwright.py
│   │   ├── stealth.py
│   │   └── router.py
│   │
│   ├── extractors/
│   │   ├── llm.py
│   │   ├── semantic.py
│   │   └── schema.py
│   │
│   ├── search/
│   │   └── ...
│   │
│   ├── monitoring/
│   │   ├── cost.py
│   │   └── logging.py
│   │
│   ├── cache/
│   │   └── ...
│   │
│   ├── cli/
│   │   └── ...
│   │
│   └── main.py
│
├── data/
│   ├── input.json
│   └── output.json
│
├── tests/
│   └── test_enrichment.py
│
├── docs/
│
├── examples/
│
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

---

# Core SoftwareBrio Files

## `dave/enrichment/schema.py`

Defines the Pydantic data models used by the enrichment pipeline.

The main schema represents:

```text
CompanyEnrichment
├── domain
├── company_overview
├── target_audience
├── contact_points[]
├── leadership[]
├── confidence_score
├── source_pages[]
├── status
└── errors[]
```

This provides a stable machine-readable contract between the LLM and the rest of the application.

## `dave/enrichment/cleaner.py`

Responsible for transforming webpage HTML into useful text.

The cleaner removes unnecessary webpage content such as:

* JavaScript
* CSS
* SVG elements
* Navigation boilerplate
* Unnecessary HTML structures

The goal is to provide the LLM with relevant webpage content rather than raw HTML.

## `dave/enrichment/discovery.py`

Implements autonomous relevant-page discovery.

Instead of blindly crawling every page, the agent scores and prioritizes links based on their relevance to lead enrichment.

Examples include:

```text
/about
/company
/team
/contact
/contact-us
/sales
/pricing
/enterprise
/customers
/solutions
```

This makes the crawler more targeted and reduces unnecessary requests and LLM tokens.

## `dave/enrichment/agent.py`

This is the main orchestration layer.

It coordinates:

```text
Domain
 ↓
Homepage
 ↓
Page Discovery
 ↓
Relevant Subpages
 ↓
Content Cleaning
 ↓
Context Aggregation
 ↓
LLM Extraction
 ↓
Evidence Verification
 ↓
Confidence Scoring
 ↓
Final Result
```

The agent processes each domain independently so one failed company does not terminate the batch.

## `dave/enrichment/scorer.py`

Calculates an evidence-grounded confidence score.

The score uses:

```text
Field Completeness
        +
Evidence Grounding
        +
Source Depth
        +
High-value Signals
        -
Error Penalty
```

The score is bounded between:

```text
0.0 → 1.0
```

---

# Input

The agent accepts a JSON list of company domains.

Example:

```json
[
  "postman.com",
  "supabase.com",
  "vapi.ai"
]
```

File:

```text
data/input.json
```

Domains are normalized before processing.

---

# Output

The agent produces:

```text
data/output.json
```

Each company follows a structured schema.

Example:

```json
{
  "domain": "example.com",
  "company_overview": "Two concise factual sentences describing the company.",
  "target_audience": "Description of the company's target customers or ICP.",
  "contact_points": [
    {
      "email": "info@example.com",
      "type": "generic",
      "source_url": "https://example.com/contact"
    }
  ],
  "leadership": [
    {
      "name": "Example Person",
      "role": "CEO",
      "linkedin_url": null
    }
  ],
  "confidence_score": 0.87,
  "source_pages": [
    "https://example.com/",
    "https://example.com/about",
    "https://example.com/contact"
  ],
  "status": "success",
  "errors": []
}
```

---

# Output Fields

| Field              | Type        | Description                             |
| ------------------ | ----------- | --------------------------------------- |
| `domain`           | `str`       | Normalized company domain               |
| `company_overview` | `str`       | Concise factual company overview        |
| `target_audience`  | `str`       | Target audience / ICP                   |
| `contact_points`   | `list`      | Public generic emails with evidence     |
| `leadership`       | `list`      | Leadership/team information             |
| `confidence_score` | `float`     | Evidence-grounded score from 0.0 to 1.0 |
| `source_pages`     | `list[str]` | Pages used during enrichment            |
| `status`           | `str`       | `success`, `partial`, or `failed`       |
| `errors`           | `list[str]` | Captured processing errors              |

---

# Anti-Hallucination Design

A major design goal is preventing the LLM from inventing lead information.

### Email Verification

An email must be present in retrieved source content before it is included.

```text
LLM extraction
      ↓
Email candidate
      ↓
Evidence search
      ↓
Found in source?
   ┌──────┴──────┐
  YES            NO
   ↓              ↓
Include          Reject
```

### LinkedIn Verification

LinkedIn URLs are only retained when they are supported by retrieved webpage evidence.

### No Fabricated Fallback Data

If information cannot be found, the system returns an empty field rather than inventing an answer.

For example:

```json
"contact_points": []
```

is preferable to fabricating an email address.

---

# Resilience

The enrichment agent is designed for real-world web failures.

## 404 / Missing Pages

A missing subpage does not terminate the company enrichment.

```text
Homepage
   ↓
/about       → 200
/contact     → 200
/team        → 404
/pricing     → 200
```

The available pages are still used.

## Invalid Domains

An invalid domain becomes:

```json
{
  "status": "failed",
  "errors": [
    "..."
  ]
}
```

Other domains continue processing.

## LLM Rate Limits

The underlying engine supports retry behavior and handles provider failures without terminating the entire batch.

## Timeouts

Individual fetch failures are isolated and recorded.

## LLM Failures

When structured extraction fails, the error is captured and the pipeline attempts fallback processing where possible.

## Partial Information

Missing information is represented explicitly.

For example:

```json
{
  "contact_points": [],
  "leadership": []
}
```

The system does not fabricate unavailable information.

---

# Fetching Strategy

The underlying DAVE engine provides multiple fetchers.

| Fetcher    | Purpose                                     |
| ---------- | ------------------------------------------- |
| HTTP       | Fast static webpages                        |
| Playwright | JavaScript-rendered websites                |
| Stealth    | Websites with stronger automation detection |
| File       | Local HTML, Markdown, JSON, text and PDF    |
| Plugin     | External/custom crawlers                    |

Automatic routing allows the agent to select an appropriate fetching mechanism.

---

# JavaScript Rendering

Some modern websites are heavily dependent on JavaScript.

For these websites, Playwright can render the page before extraction.

Installation:

```bash
python -m pip install -e ".[playwright]"
python -m playwright install chromium
```

The SoftwareBrio enrichment pipeline can therefore work with both:

```text
Static HTML
```

and:

```text
JavaScript-rendered DOM
```

---

# Caching and Rate Limiting

The underlying DAVE infrastructure provides:

* Response caching
* Domain rate limiting
* Retries
* Request delays
* Queueing
* Structured logging
* Cost tracking

These controls reduce unnecessary requests and make repeated enrichment runs more efficient.

---

# Cost Tracking

LLM usage is tracked during the enrichment process.

The demonstrated run produced:

```text
Tokens:
52,440

Estimated cost:
$0.071274
```

Cost tracking is useful for scaling the pipeline to larger lead datasets.

---

# LLM Providers

The underlying engine supports multiple providers.

Currently supported providers include:

```text
OpenAI
Anthropic
Gemini
Groq
Mistral
Ollama
Mock
```

The demonstrated SoftwareBrio run used:

```text
Provider: Groq
Model: openai/gpt-oss-20b
```

The provider and model are configurable through the CLI.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/chandramouli9392/SoftwareBrio_AI-Engineer.git
cd SoftwareBrio_AI-Engineer
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the project:

```bash
python -m pip install -e ".[dev]"
```

For JavaScript-rendered websites:

```bash
python -m pip install -e ".[playwright]"
python -m playwright install chromium
```

---

# Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the provider:

```text
DAVE_LLM_PROVIDER=groq
DAVE_LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=<your-key>
```

API keys are loaded from environment variables.

**Never commit `.env` to Git.**

The repository includes `.env` in `.gitignore`.

---

# Running the Agent

Default SoftwareBrio run:

```bash
dave enrich \
  --provider groq \
  --model openai/gpt-oss-20b \
  --input data/input.json \
  --output data/output.json
```

Short form:

```bash
dave enrich --provider groq --model openai/gpt-oss-20b --input data/input.json --output data/output.json
```

---

# Mock Run

A mock provider is available for testing without an API key:

```bash
dave enrich \
  --provider mock \
  --model mock \
  --input data/input.json \
  --output data/output.json
```

This makes local testing possible without consuming LLM credits.

---

# Testing

The project includes automated tests covering the enrichment workflow and supporting functionality.

Run:

```bash
python -m pytest tests/ -v
```

The final validation run produced:

```text
96 passed
1 skipped
```

Linting was also executed:

```bash
python -m ruff check dave/ tests/
```

Result:

```text
All checks passed!
```

---

# Test Coverage Areas

Tests cover important behaviors including:

* Schema validation
* Domain normalization
* Content cleaning
* Relevant-page discovery
* Evidence verification
* Confidence scoring
* Failure isolation
* Invalid domain handling
* Output structure
* Mock provider behavior

The purpose is to test both normal extraction and failure paths.

---

# Example End-to-End Workflow

Suppose the input is:

```json
[
  "postman.com",
  "supabase.com",
  "vapi.ai"
]
```

The system performs:

### Step 1 - Normalize Domains

```text
postman.com
supabase.com
vapi.ai
```

### Step 2 - Fetch Homepage

```text
HTTP
   or
Playwright
```

### Step 3 - Clean Content

```text
HTML
 ↓
DOM parsing
 ↓
Relevant text
```

### Step 4 - Discover Pages

Example:

```text
/about
/company
/contact
/pricing
/sales
```

### Step 5 - Fetch Selected Pages

The crawler retrieves the most relevant pages within the configured page limit.

### Step 6 - Aggregate Context

```text
Homepage
+
About
+
Contact
+
Pricing
+
Relevant company pages
```

### Step 7 - Structured LLM Extraction

The LLM receives clean contextual content and a Pydantic-defined schema.

### Step 8 - Evidence Verification

Extracted information is checked against the retrieved source text.

### Step 9 - Confidence Scoring

The system evaluates completeness and evidence grounding.

### Step 10 - Output

```text
data/output.json
```

---

# Example Demonstrated Output

For `postman.com`, the agent successfully extracted company information, target audience information, public generic contact points, and leadership information.

For `supabase.com`, the agent successfully extracted company information, target audience information, public contact points, and leadership information.

For `vapi.ai`, the agent successfully extracted company information and available leadership information while returning no public generic email addresses when none were supported by the retrieved evidence.

This demonstrates that the system does not require every field to be populated in order to complete a successful enrichment.

---

# Why This Architecture?

The implementation intentionally avoids introducing a heavy agent framework.

Instead, the workflow uses a focused custom orchestration layer:

```text
Agent
 +
Fetcher
 +
Cleaner
 +
Discovery
 +
LLM
 +
Validator
 +
Evidence Checker
 +
Scorer
```

This provides:

* Clear control flow
* Easy debugging
* Lower dependency overhead
* Deterministic preprocessing
* Explicit failure handling
* Structured outputs
* Easier testing

The existing DAVE infrastructure handles the lower-level scraping and reliability concerns while the SoftwareBrio-specific enrichment layer focuses on the business problem.

---

# Existing DAVE Infrastructure

BrioLeadEnricher builds on DAVE's existing capabilities.

DAVE provides:

* HTTP scraping
* Playwright rendering
* Stealth browser support
* Search integration
* Multi-page crawling
* Pydantic extraction
* LLM providers
* Semantic chunking
* Caching
* Rate limiting
* Retry handling
* Cost tracking
* Structured logging
* Batch processing
* Plugin support

The SoftwareBrio-specific implementation adds the domain-level enrichment workflow on top of these components.

---

# DAVE Quick Start

The underlying engine can also be used independently.

Install:

```bash
pip install dave-ai
```

Extract company information:

```bash
dave extract "https://openai.com" --recipe company_info
```

Or from Python:

```python
import dave

result = await dave.extract(
    "https://example.com",
    "get the title and description"
)

print(result)
```

---

# Built-in Recipes

DAVE includes several extraction recipes:

```text
company_info
pricing
job_listings
contact_info
product_features
reviews
```

Example:

```bash
dave extract https://example.com --recipe company_info
```

Python:

```python
import dave

company = await dave.recipes.company_info(
    "https://example.com"
)

print(company.model_dump())
```

---

# Multi-Page Crawling

The underlying engine supports bounded website crawling.

Example:

```bash
dave crawl \
  "https://example.com" \
  --recipe company_info \
  --max-pages 20 \
  --max-depth 2
```

The SoftwareBrio enrichment workflow uses a more targeted discovery strategy rather than blindly crawling every page.

---

# Search Integration

DAVE also supports web search followed by extraction.

Example:

```bash
dave search \
  "best open source CRM" \
  --recipe company_info \
  --limit 5
```

Search providers are pluggable.

This capability can be extended for future external lead discovery and LinkedIn URL discovery.

---

# Plugin Architecture

The underlying engine supports custom fetchers and search providers.

This makes the system extensible for:

* External crawlers
* Enterprise crawlers
* Authenticated browser sessions
* Proxy providers
* Custom search APIs
* Internal company databases
* Domain-specific validators
* Custom LLM routers

---

# Configuration

Example configuration:

```python
from dave.core.config import DaveConfig, LLMConfig

config = DaveConfig(
    fetcher="auto",
    llm=LLMConfig(
        provider="openai",
        model="gpt-4o-mini"
    ),
    cache_path=".dave/cache.sqlite3",
    rate_limit_per_domain=2.0,
)
```

---

# Security

API credentials are handled through environment variables.

The repository does not require API keys to be hard-coded into source files.

`.env` is excluded through `.gitignore`:

```text
.env
.env.*
!.env.example
```

Only placeholder values should be stored in `.env.example`.

Before pushing to GitHub, verify:

```bash
git status
```

and make sure `.env` is not tracked.

---

# Responsible Web Access

The system is intended for publicly accessible information.

When using the crawler:

* Respect website terms of service.
* Respect robots.txt where applicable.
* Avoid excessive request rates.
* Use rate limiting.
* Do not bypass access controls.
* Do not collect private information.
* Use public professional/company information only.

---

# Engineering Decisions

## 1. Pydantic Instead of Free-Form JSON

Pydantic provides validation and a stable contract for downstream processing.

## 2. Evidence Verification After LLM Extraction

LLMs can produce plausible but unsupported information.

Programmatic verification provides an additional safety layer.

## 3. Targeted Page Discovery

A targeted crawler reduces:

* Network requests
* Processing time
* LLM tokens
* Irrelevant context

## 4. Failure Isolation

Each company is treated as an independent unit.

This is important when processing large lead lists.

## 5. Explicit Confidence Scoring

Confidence is calculated from observable signals rather than relying entirely on an LLM-generated probability.

## 6. Cost Tracking

LLM usage is tracked so the system can be evaluated before scaling to larger datasets.

---

# Limitations

The system intentionally works only with publicly discoverable information.

Some companies may:

* Hide contact information
* Block automated browsers
* Use authentication
* Render content dynamically
* Have incomplete leadership pages
* Provide no public generic email
* Prevent indexing of LinkedIn URLs

In these cases the agent records the available information rather than inventing missing data.

A successful run therefore does not imply that every field will always be populated.

---

# Future Improvements

Possible future improvements include:

* Stronger external LinkedIn search integration
* Additional search providers
* More advanced browser-agent loops
* Optional graph-based orchestration for complex workflows
* Better SPA-specific discovery
* More domain-specific extraction validators
* Larger benchmark datasets
* OpenTelemetry tracing
* Persistent enrichment history
* Lead deduplication
* CRM integration
* Automated lead scoring
* Human review workflows

These are intentionally separated from the core enrichment pipeline so the current system remains lightweight and testable.

---

# Submission Deliverables

The repository contains the main implementation and supporting artifacts for the SoftwareBrio practical assignment.

Important files:

```text
data/input.json
data/output.json
dave/enrichment/schema.py
dave/enrichment/cleaner.py
dave/enrichment/discovery.py
dave/enrichment/agent.py
dave/enrichment/scorer.py
tests/test_enrichment.py
.env.example
README.md
LICENSE
```

---

# Assignment Mapping

| SoftwareBrio Requirement | Implementation                       |
| ------------------------ | ------------------------------------ |
| Python agent             | `dave/enrichment/agent.py`           |
| Company domain input     | `data/input.json`                    |
| Required test domains    | Postman, Supabase, Vapi              |
| Automated browsing       | HTTP + Playwright                    |
| JS rendering             | Playwright                           |
| Relevant subpages        | Autonomous page discovery            |
| Content preprocessing    | `cleaner.py`                         |
| No raw HTML to LLM       | Cleaned text/Markdown representation |
| Structured LLM output    | Pydantic schemas                     |
| Company overview         | `CompanyEnrichment`                  |
| ICP / target audience    | `target_audience`                    |
| Public emails            | `contact_points`                     |
| Leadership               | `leadership`                         |
| LinkedIn URLs            | Evidence-verified when discoverable  |
| Confidence               | Evidence-grounded scoring            |
| 404 handling             | Failure isolation                    |
| Timeouts                 | Fetcher resilience                   |
| Rate limits              | Retry/rate-limit infrastructure      |
| Missing information      | Explicit empty fields                |
| Batch resilience         | Per-domain isolation                 |
| Cost tracking            | DAVE cost tracker                    |
| Tests                    | Pytest                               |
| Linting                  | Ruff                                 |

---

# Validation Summary

Final local validation:

```text
Pytest:
96 passed, 1 skipped

Ruff:
All checks passed!
```

Live enrichment:

```text
3 / 3 companies successful
15 pages analyzed
52,440 tokens
$0.071274 estimated cost
```

---

# Conclusion

BrioLeadEnricher demonstrates an autonomous lead enrichment pipeline that combines web browsing, targeted page discovery, content preprocessing, structured LLM extraction, evidence verification, confidence scoring, and resilient batch processing.

The key design principle is:

```text
Do not trust the LLM alone.
```

Instead:

```text
Retrieve
   ↓
Clean
   ↓
Extract
   ↓
Verify
   ↓
Score
   ↓
Return structured evidence-grounded data
```

This makes the system suitable as a foundation for larger lead enrichment and sales intelligence workflows.

---

# License

The underlying DAVE project is released under the MIT License.

See:

```text
LICENSE
```

for the complete license text.

---

# Original DAVE Documentation

BrioLeadEnricher is built on top of DAVE, an AI-powered scraping and structured extraction engine.

DAVE provides:

* Zero-config extraction
* Built-in extraction recipes
* HTTP and Playwright fetching
* Search
* Multi-page crawling
* Batch processing
* Streaming extraction
* Pydantic-first extraction
* Semantic chunking
* Cost tracking
* Caching
* Retry handling
* Rate limiting
* Plugin architecture
* Multiple LLM providers
* Local file/PDF processing
* Stealth fetching
* robots.txt support

The SoftwareBrio enrichment workflow uses these capabilities as infrastructure while adding the assignment-specific autonomous lead enrichment layer.

---

## Contributing

Before opening a pull request, run:

```bash
pytest
ruff check .
python -m compileall dave
```

Contributions should improve:

* Reliability
* Extraction quality
* Testing
* Documentation
* Developer experience
* Domain-specific enrichment capabilities

```
```
