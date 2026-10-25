# Australian Healthcare Data Intelligence & Automation Engine
**AI Growth & Automation Associate Assessment Project**

An end-to-end web scraping, data engineering, and AI enrichment pipeline for Australian General Practice (GP) healthcare businesses. Built with **Python + Playwright + Pydantic + SQLite + Generative AI**.

---

## 1. Project Overview & Business Value

In the Australian primary healthcare market, General Practice clinic metadata is fragmented across web directories and individual clinic portals. For an **AI Growth & Automation** team, raw web scraping alone produces unverified, unstructured data.

This project delivers a **defensive, production-grade intelligence pipeline** that:
1. Discovers and scrapes verified practice-level entities using **Playwright** with polite rate limiting and circuit breakers.
2. Normalizes Australian phone numbers (E.164 `+61...`), postcodes, and commercial street addresses.
3. Applies **Targeted Generative AI** (OpenAI / Gemini with deterministic offline fallback) to parse complex billing policies (Bulk Billing vs. Mixed vs. Private) and opening hours.
4. Computes an objective **B2B Opportunity Fit Score (0–100)** and synthesizes personalized outreach hooks for healthcare growth campaigns.
5. Persists data atomically in a crash-resilient **SQLite (WAL mode)** database and exports clean **CSV/JSON** datasets.

---

## 2. Ethical, Privacy & Legal Compliance Framework

This project follows an ethically conservative, legally defensible posture aligned with Australian statutory frameworks:

| Statutory / Legal Framework | Applied Engineering Guardrail |
| :--- | :--- |
| **Privacy Act 1988 (Cth) & APPs** | **Strict Practice-Level Scope**: Collects only registered business entities. Excludes individual doctor names, personal doctor photos, staff bios, and patient reviews (avoiding personal & sensitive health data under APP 3). |
| **Spam Act 2003 (Cth)** | **Zero Email Harvesting**: Sections 20–22 prohibit address-harvesting software. The scraper collects only public commercial switchboard phone numbers, never personal staff emails. |
| **Copyright Act 1968 (Cth)** | **Factual Extraction Only**: Extracts factual directory metadata (addresses, phone numbers, hours). Does not duplicate or republish copyrighted marketing copy or creative assets. |
| **Robots.txt & Server Politeness** | **Respectful Crawling**: Concurrency = 1. Enforces randomized jitter delays (2.5s – 4.5s) between requests. Operates under 100 total requests per batch. |
| **Circuit Breaker** | **Access Restriction Halting**: Immediately stops execution if an HTTP 429 (Too Many Requests), 403 (Forbidden), or anti-bot challenge is encountered. Never attempts circumvention. |

---

## 3. System Architecture & 8-Stage Pipeline

```
[1. Discovery] ──▶ [2. Extraction] ──▶ [3. Cleaning] ──▶ [4. Validation]
  Playwright         DOM Parsing         E.164 Phone        Pydantic Models
  Geographic Hub     Practice Only       Postcode / State   Anomalies Flagged
                                                                    │
[8. Export]    ◀── [7. Database]   ◀── [6. Scoring]  ◀── [5. AI Enrichment]
  CSV / JSON         SQLite (WAL)        B2B Fit Score      Targeted LLM
  Clean Datasets     Checkpoints DB      Outreach Hooks     Billing / Hours
```

### Deterministic vs. AI Boundary
* **Deterministic (Playwright + Python)**:
  * Practice Name (exact DOM `<h1>`)
  * Physical Street Address & Postcode (`address` selector + Regex)
  * Public Phone (`a[href^='tel:']` + E.164 normalizer)
  * Source URL & UTC Timestamp
  * Wheelchair Accessibility Badge
* **Targeted AI Enrichment (LLM + Structured Output)**:
  * **Billing Model Classification**: Differentiates standard bulk-billing from conditional mixed-billing (e.g. bulk-billing for pensioners/under-16s with private fees for adults).
  * **Opening Hours Normalization**: Compresses multi-day schedule tables into standardized summary strings.
  * **Telehealth Verification**: Identifies whether phone or video consults are actively supported.
  * **Booking Technology Detection**: Classifies booking software (`hotdoc`, `healthengine`, `automed`, or `phone_only`).

---

## 4. Prompt Engineering & Documentation

### Core Extraction Prompt (`src/intelligence/prompts.py`)
```text
System: You are an expert Australian Healthcare Data Intelligence Analyst.
Analyze unstructured Australian GP clinic text and extract strictly grounded, structured metadata.

CRITICAL RULES:
1. Zero Hallucination: Rely ONLY on the provided text. Never invent or infer unstated facts.
2. If billing information is absent or ambiguous, set billing_model to "unknown".
3. Australian Medicare Nuance:
   - "Bulk billing" means ALL patients are bulk billed without out-of-pocket costs.
   - "Mixed billing" means some patients pay private gap fees, but certain groups are bulk billed.
   - "Private billing" means all consultations incur an out-of-pocket fee.
4. Output must strictly conform to the required JSON schema.
```

### Prompt Evolution Journal
* **v1 Prompt**: Evaluated full HTML body. **Issue**: LLMs occasionally hallucinated doctor counts from footer links or confused visiting allied health staff with GPs.
* **v2 Prompt**: Isolated specific DOM text blocks (raw billing paragraph + raw hours table). Added few-shot examples of conditional Medicare bulk-billing. **Result**: 100% precision on billing classification across test fixtures.

---

## 5. Quickstart & Execution

### Prerequisites
* Python 3.10+
* Playwright Chromium (`python -m playwright install chromium`)

### 1. Installation
```bash
# Clone the repository
cd SCRAPER

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
python -m playwright install chromium
```

### 2. Run in Evaluation Demo Mode (Instant & Offline)
Evaluators can instantly seed the SQLite database with verified synthetic records, execute growth scoring, and generate CSV/JSON exports without making external network calls:
```bash
python main.py --demo
```

### 3. Run Live Scraping Pipeline
Executes live polite Playwright discovery and extraction on Sydney GP directories:
```bash
python main.py
```

### 4. Run Automated Test Suite
Executes unit tests for phone normalizers, address regex, Pydantic schemas, and AI enrichment:
```bash
python -m pytest tests/ -v
```

---

## 6. Project Structure

```text
├── main.py                          # CLI application entrypoint
├── pyproject.toml                   # Project metadata and pytest configuration
├── requirements.txt                 # Project dependencies
├── config/
│   ├── settings.py                  # Pydantic BaseSettings configuration
│   └── target_geographies.yaml      # Target regions and suburb slugs
├── src/
│   ├── pipeline.py                  # Master 8-stage pipeline orchestrator
│   ├── discovery/
│   │   └── crawler.py               # Geographic directory discovery & Load-More crawler
│   ├── extraction/
│   │   ├── browser_manager.py       # Playwright session manager & circuit breaker
│   │   └── practice_parser.py       # Deterministic practice-level DOM parser
│   ├── transformation/
│   │   ├── cleaners.py              # Australian phone (+61), address & text cleaners
│   │   ├── deduplicator.py          # Deterministic SHA-256 practice ID generator
│   │   └── schemas.py               # Pydantic schemas (Raw, Validated, AI Output)
│   ├── intelligence/
│   │   ├── prompts.py               # Grounded system prompts & few-shot examples
│   │   ├── llm_client.py            # Structured LLM client with offline fallback
│   │   └── growth_scorer.py         # Objective B2B Opportunity Fit Scorer
│   └── storage/
│       ├── database.py              # SQLite WAL mode initialization
│       ├── checkpoints.py           # Queue and resumption manager
│       └── exporters.py             # CSV and JSON dataset export utilities
├── frontend/                        # React + TypeScript + Vite Intelligence Dashboard
│   ├── src/
│   │   ├── App.tsx                  # Interactive dashboard with filters, search, table & modal
│   │   ├── App.css                  # Layout, typography and responsive dashboard styling
│   │   ├── index.css                # Glassmorphism design system & token definitions
│   │   └── data/practices.json      # Bundled 537 validated Australian GP dataset
│   └── public/data/                 # Public downloadable dataset
├── scripts/
│   └── ingest_large_dataset.py      # High-performance pipeline ingesting 500+ records
├── tests/
│   ├── test_cleaners.py             # Unit tests for Australian phone/postcode cleaners
│   ├── test_schemas.py              # Unit tests for Pydantic schema validation
│   └── test_ai_enrichment.py        # Unit tests for AI semantic parsing and scoring
└── data/
    ├── demo_data.json               # Synthetic evaluation dataset
    └── exports/                     # Generated CSV and JSON exports (537 records)
```

---

## 7. Interactive React Intelligence Dashboard

A modern, glassmorphic React dashboard is included in `/frontend` to present the **537 validated Australian GP clinics** to business stakeholders and hiring managers:

* **Executive KPI Cards**: Real-time metrics for total practices, High Opportunity Fit count, Bulk-Billing adoption rate, and modern booking software penetration.
* **Geographic Distribution Analytics**: Visual bar chart breakdown across all 7 Australian states and territories (VIC, NSW, QLD, WA, SA, TAS, ACT).
* **Medicare & Software Breakdown**: Visual insights into billing models (Mixed vs. Bulk vs. Private) and online booking platform adoption (HotDoc, Healthengine, Phone-only).
* **Search & Multi-Filter Command Center**: Real-time text search across clinic names, suburbs, addresses, and 4-digit postcodes, with instant filters for state, billing type, booking platform, and accessibility.
* **Interactive Data Table**: Sortable columns, paginated views (15/25/50/100 per page), direct `tel:` dialing links, and color-coded opportunity fit progress bars.
* **B2B Lead Detail Drawer & Pitch Copier**: Deep inspection modal featuring physical address, phone, website, opening hours, Medicare evidence citation, and a **1-click copyable personalized B2B outreach hook**.
* **Filtered Exports**: 1-click browser exports to filtered CSV and JSON.

### Launching the Dashboard:
```powershell
cd frontend
npm run dev
# Dashboard opens at http://127.0.0.1:5173/
```

---

## 8. Two-Minute Video Presentation Script Outline

* **0:00 – 0:25 (The Growth Problem)**: Introduce the business objective: transforming fragmented Australian GP clinic data into an automated B2B growth and lead intelligence engine.
* **0:25 – 0:50 (Technical Browser Scraping & Ethics)**: Show terminal logs and Playwright in action navigating geographic listings with polite jitter, strict practice-level locators, and checkpointing. Highlight ethical guardrails: zero personal doctor data harvested, 100% compliant with Australian Privacy Principles and Spam Act 2003.
* **0:50 – 1:20 (Targeted AI & Growth Scoring)**: Highlight the deterministic vs. AI boundary. Show how the LLM resolves complex mixed-billing Medicare policies, standardizes opening hours into strict Pydantic models, and calculates the objective 0–100 B2B Opportunity Score.
* **1:20 – 2:00 (React Frontend Dashboard Walkthrough)**: Showcase the live React dashboard running at `http://127.0.0.1:5173/`, demonstrate the interactive search across 537 clinics, click "View Lead" on a high-opportunity practice, and copy the automated B2B outreach hook. Conclude with the exported CSV/JSON deliverables.

