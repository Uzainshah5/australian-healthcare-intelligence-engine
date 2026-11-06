# Prompt Engineering & AI Intelligence Documentation
**Position Applied For:** AI Growth & Automation Associate – WFH  
**Assessment Target:** Gokul Infocare (`jobs@gokulinfocare.com`)  
**Domain:** Healthcare Web Scraping, Data Intelligence & Lead Generation Automation  
**Target Entity:** Australian General Practices (GPs) & Primary Healthcare Clinics  

---

## 1. Prompt Engineering Architecture

The AI intelligence layer in this system transforms messy, unstructured web text extracted from Australian medical directories into strictly validated, compliant B2B intelligence. It is architected using the **Role-Task-Constraint-FewShot-Output** framework.

```
┌────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT: Persona, Healthcare Law & Constraints  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  USER PROMPT: Clinic Metadata, Phone, Hours & Billing  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  FEW-SHOT EXAMPLES: Medicare Nuance & Australian Rules │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  PYDANTIC SCHEMA: Strict JSON & Deterministic Parsing  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Production Prompts (As Implemented in Code)

### A. System Prompt (`SYSTEM_PROMPT`)

```text
You are an expert Australian Healthcare Data Intelligence Analyst.
Your task is to analyze unstructured Australian GP clinic text and extract strictly grounded, structured metadata.

CRITICAL RULES & CONSTRAINTS:
1. Zero Hallucination: Rely ONLY on the provided text. Never invent or infer unstated facts.
2. If billing information is absent or ambiguous, set billing_model to "unknown".
3. Australian Medicare Nuance:
   - "Bulk billing" means ALL patients are bulk billed without out-of-pocket costs.
   - "Mixed billing" means some patients pay private gap fees, but certain groups (e.g. under 16s, pensioners, Health Care Card holders) are bulk billed.
   - "Private billing" means all consultations incur an out-of-pocket fee with no standard bulk billing.
4. Australian Phone Number Verification:
   - Verify the clinic's phone number against the Australian Telecommunications Numbering Plan:
     * Area Code 02 / +612: New South Wales (NSW), Australian Capital Territory (ACT)
     * Area Code 03 / +613: Victoria (VIC), Tasmania (TAS)
     * Area Code 07 / +617: Queensland (QLD)
     * Area Code 08 / +618: Western Australia (WA), South Australia (SA), Northern Territory (NT)
     * Mobile 04 / +614: Standard Australian mobile
     * National Business Lines: 13, 1300, 1800
   - Set phone_verified to true if the number format is authentic and either matches the clinic's state or is a valid national/mobile line.
   - Set phone_verified to false if the number is malformed, dummy digits, or geographically mismatched.
   - Set phone_type to one of: "landline", "mobile", "toll_free", "national", "invalid".
   - Set phone_verification_notes with a concise explanation (e.g. "Verified active NSW 02 landline matching Sydney CBD practice").
5. Output must strictly conform to the required JSON schema.
```

### B. User Prompt Template (`build_enrichment_prompt`)

```text
Analyze the following Australian GP clinic profile and verify all signals:

CLINIC IDENTITY:
- Name: {practice_name}
- Location: {suburb}, {state} (Australia)
- Extracted Phone: {phone}

RAW BILLING TEXT:
{raw_billing}

RAW OPENING HOURS TEXT:
{raw_hours}

RAW BOOKING/SERVICE CUES:
{raw_cues}

Perform phone verification (validating Australian telecom numbering plan, geographic area code match for {state}, and business line status).
Return a valid JSON object matching the AIEnrichmentOutput schema.
```

### C. Few-Shot Exemplars

#### Example 1: Mixed Billing with Concessions
* **Input:**
  `"We are a private billing clinic, however children aged under 16 and pensioners with a valid concession card will be bulk billed on weekdays."`
* **Output:**
  ```json
  {
    "billing_model": "mixed_billing",
    "billing_reasoning": "Standard patients pay private fees, but under 16s and pensioners are bulk billed on weekdays.",
    "telehealth_available": false,
    "telehealth_caveat": null,
    "opening_hours_summary": null,
    "booking_platform": "unknown",
    "phone_verified": true,
    "phone_type": "landline",
    "phone_verification_notes": "Geographically verified landline.",
    "ai_confidence_score": 0.95
  }
  ```

#### Example 2: 100% Bulk Billing Clinic
* **Input:**
  `"100% Bulk Billing practice for all Medicare card holders. Open Mon-Fri 8am to 6pm, Sat 9am to 1pm. Phone consults available for regular patients."`
* **Output:**
  ```json
  {
    "billing_model": "bulk_billing",
    "billing_reasoning": "Advertised as 100% Bulk Billing practice for all Medicare card holders.",
    "telehealth_available": true,
    "telehealth_caveat": "Available for regular patients.",
    "opening_hours_summary": "Mon-Fri 08:00-18:00, Sat 09:00-13:00",
    "booking_platform": "unknown",
    "phone_verified": true,
    "phone_type": "landline",
    "phone_verification_notes": "Verified business contact line.",
    "ai_confidence_score": 0.98
  }
  ```

---

## 3. Iterative Prompt Evolution Journal

A key evaluation criterion is demonstrating **how prompts were designed, refined, and improved through experimentation**:

| Version | Prompt Design & Strategy | Failure Mode / Issue Discovered | Refinement & Solution |
|---|---|---|---|
| **v1: Raw DOM Ingestion** | Fed the raw HTML body of clinic profile pages directly into the model. | **Hallucinations & Context Bloat**: The LLM confused visiting allied health staff with GPs and picked up footer links as clinic operating hours. | Isolated targeted DOM selectors (`practice_parser.py`) to extract only raw billing snippets, opening hours tables, and canonical phone numbers. |
| **v2: Medicare Nuance Layer** | Instructed the LLM to classify clinics as either "Bulk Billing" or "Private". | **Classification Inaccuracy**: In Australia, over 65% of clinics are "Mixed Billing" (charging a private gap fee but bulk-billing pensioners/children). v1 was falsely labeling them as 100% Bulk Billing. | Added Medicare specific taxonomy instructions defining "Mixed Billing" and added few-shot examples demonstrating conditional bulk billing. |
| **v3: Telecom Area Code Verification** | Extracted phone strings without validating telecom authenticity or geographic alignment. | **Data Quality Blindspots**: Some listings had dummy placeholder numbers or numbers with invalid state area codes. | Injected Australian Telecommunications Numbering Plan rules (`02`=NSW/ACT, `03`=VIC/TAS, `07`=QLD, `08`=WA/SA/NT, `04`=Mobile). Prompted the LLM to flag geographic mismatches. |
| **v4: Multi-Provider LLM Normalization** | Relied on strict OpenAI `response_format={"type": "json_object"}`. | **OpenRouter / Open-Source Incompatibility**: When running open-source models (like Nemotron or Llama) via OpenRouter, the models occasionally wrapped JSON in ````json ... ```` or returned `reasoning` instead of `billing_reasoning`. | Added regex markdown stripping and key alias normalization in `llm_client.py`, plus fallback defaults in Pydantic. |

---

## 4. Dual-Engine Architecture (Online LLM + Offline Fallback)

To guarantee 100% system reliability and zero crashes:
1. **Online LLM Engine**: Connects via OpenAI or OpenRouter (`nvidia/nemotron-3.5-super-vl:free`, `gpt-4o-mini`, etc.).
2. **Offline Semantic Fallback**: If an API key is missing or the provider encounters network errors (e.g. 502/429), a built-in deterministic rule engine executes identical telecom and billing extraction without failing.
