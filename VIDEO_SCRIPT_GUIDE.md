# 2-Minute Video Presentation Script & Talking Points
**Role:** AI Growth & Automation Associate – WFH  
**Recipient:** Gokul Infocare (`jobs@gokulinfocare.com`)  
**Project:** Australian GP Healthcare Intelligence Hub & Lead Generation Automation  

---

## Video Outline & Timing Breakdown (Target: 2 min 30 sec - 3 min)

| Timestamp | Section | Visual on Screen | Key Talking Points |
|---|---|---|---|
| **0:00 - 0:30** | **1. Introduction & AI Tools** | Show the React Dashboard (`http://127.0.0.1:5173`) | Introduce yourself, state the problem in Australian healthcare B2B lead gen, and mention AI tools (OpenRouter Nemotron, OpenAI SDK, Pydantic, Playwright). |
| **0:30 - 1:00** | **2. Prompt Engineering & Evolution** | Open `src/intelligence/prompts.py` in VS Code | Explain the Persona-Constraint-FewShot structure. Highlight the prompt evolution from v1 (raw HTML hallucination) to v4 (Australian Medicare nuances & telecom area code verification). |
| **1:00 - 1:35** | **3. Approach & Architecture** | Show the terminal running `python main.py` or pipeline diagram | Explain the 8-stage pipeline: Playwright stealth scraping, E.164 phone normalization, SHA-256 deduplication, AI enrichment, SQLite WAL checkpoints, and CSV/JSON exports. |
| **1:35 - 2:05** | **4. Challenges & Problem-Solving** | Show `src/storage/database.py` or `llm_client.py` | Mention 3 real challenges: (1) Client-side SPA hydration solved with Playwright waits, (2) Open-source LLM output formatting solved with regex sanitizers, (3) Privacy Act compliance (business-only entities). |
| **2:05 - 2:40** | **5. Live Demo & Final Outcome** | Back to the React Dashboard | Filter clinics by State, search for a suburb, open the **Lead Detail Modal**, show the **AI Phone Verification** badge, and demonstrate the **1-Click Copyable B2B Sales Pitch**. |

---

## Word-for-Word Video Script

### 0:00 - 0:30 | Section 1: Introduction & AI Tools
> *"Hello! My name is [Your Name], and this is my submission for the AI Growth & Automation Associate assessment at Gokul Infocare.*  
> *For this challenge, I chose the **Web Scraping, Data Intelligence, and Automation** track in the healthcare domain. I built an end-to-end automated market intelligence engine and executive dashboard for Australian General Practices.*  
> *For the AI layer, I leveraged **OpenRouter** and **OpenAI APIs** utilizing models like **Nvidia Nemotron** and **GPT-4o-mini**, combined with **Pydantic** for strict structured data enforcement and **Playwright** for stealth web automation."*

### 0:30 - 1:00 | Section 2: Prompt Engineering & Evolution
> *"One of the primary focuses of this project was prompt engineering.*  
> *Instead of simple zero-shot prompts, I implemented a strict **Role-Constraint-FewShot** framework.*  
> *Through experimentation, my prompts evolved through four iterations:*  
> *In **v1**, passing raw HTML led to hallucinated doctor names from footer links.*  
> *In **v2**, I introduced Australian Medicare domain knowledge—specifically defining the difference between bulk-billing and mixed-billing.*  
> *In **v3**, I integrated telecom rules: verifying Australian area codes (like 02 for NSW and 03 for Victoria) to flag mismatching or dummy phone numbers.*  
> *And in **v4**, I engineered resilient JSON sanitization so open-source models format structured responses without breaking the Pydantic schema."*

### 1:00 - 1:35 | Section 3: Architecture & Engineering Approach
> *"My approach was to design a production-grade, 8-stage pipeline:*  
> *Stage 1 discovers clinics dynamically across major Australian cities.*  
> *Stage 2 executes polite browser extraction with random delays to respect website servers.*  
> *Stage 3 normalizes phone numbers to the international E.164 standard.*  
> *Stage 4 uses SHA-256 digital fingerprinting to guarantee zero duplicate records.*  
> *Stage 5 runs the AI enrichment and calculates a proprietary **Lead Opportunity Score from 1 to 100**, drafting a tailored B2B outreach hook for sales reps.*  
> *And Stage 6 stores the records in an **SQLite** database with Write-Ahead Logging for crash resilience, exporting directly to CSV and JSON."*

### 1:35 - 2:05 | Section 4: Challenges & Problem Solving
> *"During development, I overcame three major challenges:*  
> *First, modern medical directories use JavaScript SPAs that fail with basic HTTP scrapers. I solved this by managing headless Chromium browser contexts with Playwright.*  
> *Second, API rate limits or third-party server errors. I engineered a **two-tier architecture**: if OpenRouter or OpenAI has an outage, the system seamlessly uses a deterministic semantic fallback parser so the pipeline never crashes.*  
> *Third, compliance. I ensured the pipeline strictly complies with the **Australian Privacy Act 1988** by scraping only business-level clinic entities and ignoring private doctor or patient details."*

### 2:05 - 2:40 | Section 5: Live Demonstration & Impact
> *"Here is the live outcome: our interactive React intelligence dashboard.*  
> *We have over 540 genuine Australian GP practices indexed.*  
> *Executives can view real-time state distributions, filter by billing models or booking technology, and search instantly.*  
> *When we click 'View Lead' on any clinic, we see full contact details, the **AI Telecom Verification status**, and a **1-click copyable B2B sales pitch** tailored specifically to that clinic's operational gaps.*  
> *Thank you for your time, and I look forward to discussing how I can bring this automation and AI mindset to Gokul Infocare!"*
