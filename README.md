<div align="center">

# ⚡ BrioLeadEnricher

### 🤖 Autonomous Lead Enrichment Agent

**Turn company domains into verified, structured lead intelligence — autonomously.**

<p>
  <img src="https://img.shields.io/badge/AI%20Agent-8A2BE2?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-Powered-FF6F00?style=for-the-badge" />
</p>

<p>
  <img src="https://img.shields.io/badge/Tests-96%20Passed-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Production%20Ready-00A67E?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" />
</p>

<br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=190&section=header&text=BrioLeadEnricher&fontSize=58&fontAlignY=35&animation=twinkling&fontColor=ffffff" width="100%"/>

</div>

---

# 🧠 What is BrioLeadEnricher?

**BrioLeadEnricher** is an autonomous web-intelligence pipeline that accepts a list of company domains and transforms publicly available web content into **structured, evidence-grounded company intelligence**.

The agent autonomously:

* 🔎 Discovers relevant company pages
* 🌐 Fetches static and JavaScript-rendered websites
* 🧹 Cleans webpage content
* 🧠 Extracts structured information using an LLM
* 🛡️ Verifies extracted evidence
* 📊 Calculates an evidence-grounded confidence score
* 🚨 Isolates failures between companies
* 📦 Produces machine-readable JSON

---

# ⚡ The Core Idea

```text
                    🌐 COMPANY DOMAIN
                           │
                           ▼
                 ┌───────────────────┐
                 │ 🔎 DISCOVERY      │
                 │                   │
                 │ About             │
                 │ Team              │
                 │ Contact           │
                 │ Sales             │
                 │ Pricing           │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ 🕷️ SMART BROWSER │
                 │                   │
                 │ HTTP              │
                 │ Playwright       │
                 │ Retries           │
                 │ Caching           │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ 🧹 CONTENT CLEANER│
                 │                   │
                 │ HTML → Text       │
                 │ Remove JS / CSS   │
                 │ Remove SVG        │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ 🧠 LLM EXTRACTION │
                 │                   │
                 │ Company           │
                 │ ICP               │
                 │ Emails            │
                 │ Leadership        │
                 │ LinkedIn          │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ 🛡️ VERIFICATION   │
                 │                   │
                 │ Is the information│
                 │ actually supported│
                 │ by the source?    │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ 📊 CONFIDENCE     │
                 │                   │
                 │ Completeness      │
                 │ Grounding         │
                 │ Source Depth      │
                 │ High-value Signals│
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ 📦 STRUCTURED JSON│
                 │                   │
                 │ data/output.json  │
                 └───────────────────┘
```

---

# 🎯 What It Does

## 🔎 Autonomous Website Enrichment

The agent receives **only company domains** and determines which pages are useful for enrichment.

It prioritizes pages such as:

```text
/about
/company
/team
/leadership
/contact
/sales
/pricing
/enterprise
/customers
/solutions
```

This targeted discovery approach avoids blindly crawling entire websites.

---

# 🌐 JavaScript-Aware Browsing

Modern websites are not always simple HTML pages.

BrioLeadEnricher uses the underlying DAVE infrastructure to support:

```text
                 🌐 WEBSITE
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
     Static HTML          JavaScript App
          │                     │
          ▼                     ▼
        HTTP                Playwright
          │                     │
          └──────────┬──────────┘
                     ▼
              🧠 CLEAN CONTENT
```

Supported capabilities include:

* HTTP fetching
* Playwright rendering
* Automatic fetcher selection
* Stealth fetching
* Retry handling
* Rate limiting
* Caching

---

# 🧹 Content Cleaning Pipeline

Raw HTML is **not directly passed to the LLM**.

Instead:

```text
Raw HTML
   │
   ▼
DOM Parsing
   │
   ▼
Remove Scripts
   │
   ▼
Remove Styles
   │
   ▼
Remove SVG
   │
   ▼
Remove Boilerplate
   │
   ▼
Extract Meaningful Text
   │
   ▼
Clean Markdown / Text
   │
   ▼
🧠 LLM
```

This creates a cleaner intermediate representation and reduces unnecessary context before LLM processing.

---

# 🧠 Structured LLM Extraction

Instead of depending on free-form LLM responses, the system constrains extraction using **Pydantic schemas**.

```text
                🧠 LLM
                  │
                  ▼
          ┌───────────────┐
          │ Pydantic      │
          │ Schema        │
          └───────┬───────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ CompanyEnrichment    │
       ├──────────────────────┤
       │ Company Overview     │
       │ Target Audience / ICP│
       │ Contact Points       │
       │ Leadership           │
       │ LinkedIn URLs        │
       │ Confidence           │
       │ Source Pages         │
       │ Status               │
       │ Errors               │
       └──────────────────────┘
```

This creates a stable machine-readable contract between the LLM and the rest of the application.

---

# 🛡️ Evidence-Grounded Extraction

One of the core design principles is:

# **Don't trust the LLM alone.**

The pipeline verifies extracted information against retrieved webpage evidence.

```text
          🧠 LLM
            │
            ▼
    Proposed Information
            │
            ▼
    🔎 Search Retrieved Evidence
            │
            ▼
     Does source support it?
          /       \
        YES        NO
         │          │
         ▼          ▼
      INCLUDE     REJECT
```

Emails and LinkedIn URLs are checked against retrieved evidence before being retained.

---

# 📊 Confidence Scoring

The confidence score is calculated from observable signals instead of simply trusting a model-generated probability.

| Dimension          |  Weight |
| ------------------ | ------: |
| Field Completeness | **35%** |
| Evidence Grounding | **35%** |
| Source Depth       | **15%** |
| High-value Signals | **15%** |

Errors can reduce the final score.

```text
Field Completeness
       +
Evidence Grounding
       +
Source Depth
       +
High-Value Signals
       -
Error Penalty
       │
       ▼
📊 CONFIDENCE SCORE
       │
       ▼
    0.0 → 1.0
```

---

# 🛡️ Anti-Hallucination Architecture

BrioLeadEnricher explicitly avoids fabricating unavailable information.

### Email

```text
LLM Candidate
     │
     ▼
Evidence Search
     │
     ▼
Found?
 ┌───┴───┐
YES     NO
 │       │
 ▼       ▼
Keep   Reject
```

### LinkedIn

LinkedIn URLs are retained only when supported by retrieved webpage evidence.

### Missing Data

If information cannot be found:

```json
{
  "contact_points": []
}
```

is preferred over inventing an email address.

---

# ⚙️ Failure Isolation

A single failed company should **not terminate the complete batch**.

```text
postman.com
     │
     ▼
  ✅ SUCCESS

supabase.com
     │
     ▼
  ✅ SUCCESS

invalid-domain.example
     │
     ▼
  ❌ FAILED

vapi.ai
     │
     ▼
  ✅ SUCCESS
```

Each company is processed independently, allowing the remaining batch to continue when one domain fails.

---

# 🏗️ Architecture

```text
                    📄 data/input.json
                    Company Domains
                           │
                           ▼
                 ┌───────────────────┐
                 │ Domain Normalizer  │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Homepage Fetch    │
                 │ HTTP / Playwright │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Content Cleaner   │
                 │ HTML → Text       │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Page Discovery    │
                 └─────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           /about       /contact      /pricing
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Context           │
                 │ Aggregation       │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Structured LLM    │
                 │ Extraction        │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Evidence           │
                 │ Verification       │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Markdown           │
                 │ Sanitization       │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Confidence Scoring │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Status             │
                 │ Determination      │
                 └─────────┬─────────┘
                           │
                           ▼
                    📦 output.json
```

---

# 🧩 Core Architecture

```text
              ┌──────────────────────────┐
              │     BrioLeadEnricher     │
              └────────────┬─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
     🔎 Discovery      🌐 Fetchers       🧠 LLM
          │                │                │
          │          ┌─────┼─────┐          │
          │          │     │     │          │
          │         HTTP Playwright Stealth │
          │          │     │     │          │
          └──────────┴─────┼─────┴──────────┘
                           │
                           ▼
                    🧹 Cleaner
                           │
                           ▼
                    🛡️ Validator
                           │
                           ▼
                    📊 Scorer
                           │
                           ▼
                     📦 JSON
```

---

# 📁 Project Structure

```text
BrioLeadEnricher/
│
├── 📁 dave/
│   │
│   ├── 📁 enrichment/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── cleaner.py
│   │   ├── discovery.py
│   │   ├── schema.py
│   │   └── scorer.py
│   │
│   ├── 📁 core/
│   │   ├── engine.py
│   │   ├── config.py
│   │   ├── retries.py
│   │   ├── queue.py
│   │   └── rate_limit.py
│   │
│   ├── 📁 fetchers/
│   │   ├── http.py
│   │   ├── playwright.py
│   │   ├── stealth.py
│   │   └── router.py
│   │
│   ├── 📁 extractors/
│   │   ├── llm.py
│   │   ├── semantic.py
│   │   └── schema.py
│   │
│   ├── 📁 search/
│   │
│   ├── 📁 monitoring/
│   │   ├── cost.py
│   │   └── logging.py
│   │
│   ├── 📁 cache/
│   │
│   ├── 📁 cli/
│   │
│   └── main.py
│
├── 📁 data/
│   ├── input.json
│   └── output.json
│
├── 📁 tests/
│   └── test_enrichment.py
│
├── 📁 docs/
├── 📁 examples/
│
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

---

# 🔬 The Enrichment Agent

The central orchestration layer coordinates:

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

The agent processes each domain independently so one failed company does not terminate the complete batch.

---

# 📦 Input

The agent accepts a JSON list of company domains.

```json
[
  "postman.com",
  "supabase.com",
  "vapi.ai"
]
```

Input file:

```text
data/input.json
```

Domains are normalized before processing.

---

# 📤 Output

The final structured result is written to:

```text
data/output.json
```

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

# 📊 Output Schema

| Field              | Type        | Description                         |
| ------------------ | ----------- | ----------------------------------- |
| `domain`           | `str`       | Normalized company domain           |
| `company_overview` | `str`       | Concise factual overview            |
| `target_audience`  | `str`       | Target audience / ICP               |
| `contact_points`   | `list`      | Public generic emails with evidence |
| `leadership`       | `list`      | Leadership/team information         |
| `confidence_score` | `float`     | Evidence-grounded score             |
| `source_pages`     | `list[str]` | Pages used                          |
| `status`           | `str`       | `success`, `partial`, or `failed`   |
| `errors`           | `list[str]` | Captured processing errors          |

---

# 🧪 Demonstrated Run

The implementation was tested against:

```text
postman.com
supabase.com
vapi.ai
```

The demonstrated command used:

```bash
dave enrich \
  --provider groq \
  --model openai/gpt-oss-20b \
  --input data/input.json \
  --output data/output.json
```

---

# 📈 Results

| Company          | Status    | Confidence | Pages | Contacts | Leaders |
| ---------------- | --------- | ---------: | ----: | -------: | ------: |
| **postman.com**  | ✅ success |   **0.92** |     5 |        3 |       3 |
| **supabase.com** | ✅ success |   **0.92** |     5 |        5 |       2 |
| **vapi.ai**      | ✅ success |   **0.71** |     5 |        0 |       1 |

### Batch Summary

```text
Companies processed:  3
Successful:           3
Partial:              0
Failed:               0

Pages analyzed:       15
Tokens used:          52,440
Estimated cost:       $0.071274
```

---

# 💰 Cost Tracking

LLM usage is tracked during enrichment.

```text
┌─────────────────────────────┐
│       LIVE RUN METRICS      │
├─────────────────────────────┤
│                             │
│  📄 Pages       15          │
│  🧠 Tokens      52,440      │
│  💵 Cost        $0.071274   │
│                             │
└─────────────────────────────┘
```

This provides visibility into the cost of scaling enrichment workflows.

---

# 🤖 LLM Providers

The underlying engine supports:

```text
OpenAI
Anthropic
Gemini
Groq
Mistral
Ollama
Mock
```

The demonstrated run used:

```text
Provider → Groq
Model    → openai/gpt-oss-20b
```

---

# 🌐 Fetching Strategy

| Fetcher       | Purpose                         |
| ------------- | ------------------------------- |
| 🌐 HTTP       | Fast static webpages            |
| 🎭 Playwright | JavaScript-rendered websites    |
| 🥷 Stealth    | Stronger automation detection   |
| 📄 File       | HTML, Markdown, JSON, text, PDF |
| 🔌 Plugin     | External/custom crawlers        |

Automatic routing allows the system to select an appropriate fetching mechanism.

---

# ⚙️ Installation

```bash
git clone https://github.com/chandramouli9392/SoftwareBrio_AI-Engineer.git

cd SoftwareBrio_AI-Engineer

python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### Install

```bash
python -m pip install -e ".[dev]"
```

### Playwright Support

```bash
python -m pip install -e ".[playwright]"
python -m playwright install chromium
```

---

# 🔐 Environment Configuration

Create your environment file:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Example:

```env
DAVE_LLM_PROVIDER=groq
DAVE_LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=<your-key>
```

> 🔒 Never commit `.env` to GitHub.

---

# 🚀 Run the Agent

```bash
dave enrich \
  --provider groq \
  --model openai/gpt-oss-20b \
  --input data/input.json \
  --output data/output.json
```

Or:

```bash
dave enrich --provider groq --model openai/gpt-oss-20b --input data/input.json --output data/output.json
```

---

# 🧪 Mock Mode

You can run the pipeline without an API key:

```bash
dave enrich \
  --provider mock \
  --model mock \
  --input data/input.json \
  --output data/output.json
```

This allows local testing without consuming LLM credits.

---

# ✅ Testing

Run the automated test suite:

```bash
python -m pytest tests/ -v
```

Validation result:

```text
96 passed
1 skipped
```

Linting:

```bash
python -m ruff check dave/ tests/
```

Result:

```text
All checks passed!
```

---

# 🔄 End-to-End Workflow

```text
                 📂 INPUT
                    │
                    ▼
             🌐 DOMAIN NORMALIZE
                    │
                    ▼
             🕷️ FETCH WEBSITE
                    │
                    ▼
             🧹 CLEAN CONTENT
                    │
                    ▼
             🔎 DISCOVER PAGES
                    │
                    ▼
             📄 FETCH RELEVANT
                    │
                    ▼
             🧩 AGGREGATE CONTEXT
                    │
                    ▼
             🧠 LLM EXTRACTION
                    │
                    ▼
             🛡️ VERIFY EVIDENCE
                    │
                    ▼
             📊 SCORE CONFIDENCE
                    │
                    ▼
             📦 STRUCTURED JSON
```

---

# 🧠 Engineering Philosophy

The system intentionally avoids blindly trusting an LLM.

Instead:

```text
       RETRIEVE
           ↓
         CLEAN
           ↓
        EXTRACT
           ↓
        VERIFY
           ↓
         SCORE
           ↓
        OUTPUT
```

This architecture combines deterministic preprocessing and verification with LLM-based extraction.

---

# 🏆 Key Engineering Decisions

### 1️⃣ Pydantic Instead of Free-Form JSON

Provides a stable contract for downstream processing.

### 2️⃣ Evidence Verification

Adds a verification layer after LLM extraction.

### 3️⃣ Targeted Page Discovery

Reduces unnecessary:

* Network requests
* Processing
* LLM tokens
* Irrelevant context

### 4️⃣ Failure Isolation

Each company is treated independently.

### 5️⃣ Explicit Confidence Scoring

Uses observable signals instead of relying entirely on an LLM-generated probability.

### 6️⃣ Cost Tracking

Makes the system easier to evaluate before scaling.

---

# 🛡️ Resilience

BrioLeadEnricher handles real-world web failures including:

```text
❌ 404 Pages
❌ Invalid Domains
⏱️ Timeouts
🚦 Rate Limits
🔁 Fetch Failures
🧠 LLM Failures
📭 Missing Information
```

Rather than terminating the entire batch, failures are captured and represented in the output.

---

# 🔌 Plugin Architecture

The underlying engine supports extensible:

* Custom fetchers
* Search providers
* External crawlers
* Enterprise crawlers
* Authenticated browser sessions
* Proxy providers
* Custom search APIs
* Internal company databases
* Domain-specific validators
* Custom LLM routers

---

# 🔮 Future Improvements

Potential extensions include:

```text
🔎 Stronger LinkedIn Search
🌐 Additional Search Providers
🤖 Advanced Browser-Agent Loops
🧠 Graph-Based Orchestration
⚡ Better SPA Discovery
🛡️ More Extraction Validators
📊 Larger Benchmark Datasets
📡 OpenTelemetry Tracing
🗃️ Persistent Enrichment History
🔗 Lead Deduplication
📇 CRM Integration
🎯 Automated Lead Scoring
👤 Human Review Workflows
```

---

# ⚠️ Limitations

The system works with publicly discoverable information.

Some websites may:

* Hide contact information
* Block automated browsers
* Require authentication
* Render content dynamically
* Have incomplete leadership pages
* Provide no public generic email
* Prevent indexing of LinkedIn URLs

When information is unavailable, the system records the missing information instead of fabricating it.

---

# 🔒 Responsible Web Access

The system is intended for publicly accessible information.

When using the crawler:

* Respect website terms of service
* Respect robots.txt where applicable
* Avoid excessive request rates
* Use rate limiting
* Do not bypass access controls
* Do not collect private information
* Use public professional/company information only

---

# 🧰 Technology Stack

<div align="center">

| Layer           | Technology                  |
| --------------- | --------------------------- |
| 🐍 Language     | Python                      |
| 🧠 Intelligence | LLMs                        |
| 📐 Schema       | Pydantic                    |
| 🌐 Browser      | Playwright                  |
| 🕷️ Fetching    | HTTP / Playwright / Stealth |
| 🧹 Processing   | HTML → Markdown / Text      |
| 🔎 Discovery    | Autonomous Page Discovery   |
| 🛡️ Validation  | Evidence Verification       |
| 📊 Scoring      | Confidence Scoring          |
| 🧪 Testing      | Pytest                      |
| 🔍 Linting      | Ruff                        |
| 💾 Output       | Structured JSON             |

</div>

---

# 📊 Project at a Glance

```text
╔══════════════════════════════════════════════╗
║            ⚡ BrioLeadEnricher               ║
╠══════════════════════════════════════════════╣
║                                              ║
║  🤖 Autonomous Web Intelligence              ║
║                                              ║
║  🔎 Autonomous Page Discovery                ║
║  🌐 JavaScript-Aware Browsing               ║
║  🧹 Content Cleaning                        ║
║  🧠 Structured LLM Extraction               ║
║  🛡️ Evidence Verification                  ║
║  📊 Confidence Scoring                      ║
║  🚨 Failure Isolation                      ║
║  💰 Cost Tracking                           ║
║  📦 Machine-Readable JSON                   ║
║                                              ║
║  Tests: 96 Passed / 1 Skipped               ║
║                                              ║
╚══════════════════════════════════════════════╝
```

---

# 🎯 The Bigger Vision

BrioLeadEnricher can serve as the intelligence layer between:

```text
                 🌐 PUBLIC WEB
                       │
                       ▼
              🤖 ENRICHMENT AGENT
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       COMPANY       CONTACT       LEADERS
       INTEL         DATA          INFO
          │            │            │
          └────────────┼────────────┘
                       ▼
                📊 STRUCTURED DATA
                       │
                       ▼
                🎯 SALES INTELLIGENCE
                       │
                       ▼
                 🔗 CRM / WORKFLOW
```

The core architecture provides a foundation for larger lead-enrichment and sales-intelligence workflows.

---

# 👨‍💻 Author

<div align="center">

# Chandramouli Boppana

### AI Engineer • Generative AI Builder • AI Agent Developer

Building intelligent systems that transform unstructured web information into structured, actionable intelligence.

<br>

<a href="https://github.com/chandramouli9392">
<img src="https://img.shields.io/badge/GitHub-ChandramouliBoppana-181717?style=for-the-badge&logo=github" />
</a>

</div>

---

# ⭐ Support the Project

If you find **BrioLeadEnricher** interesting:

⭐ Star the repository

🍴 Fork the project

🐛 Report issues

💡 Suggest improvements

🤝 Contribute

---

<div align="center">

## ⚡ BrioLeadEnricher

### Retrieve → Clean → Extract → Verify → Score

**Turn company domains into evidence-grounded lead intelligence.**

<br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=120&section=footer&animation=twinkling" width="100%"/>

</div>
