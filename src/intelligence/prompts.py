import json

SYSTEM_PROMPT = """You are an expert Australian Healthcare Data Intelligence Analyst.
Your task is to analyze unstructured Australian GP clinic text and extract strictly grounded, structured metadata.

CRITICAL RULES:
1. Zero Hallucination: Rely ONLY on the provided text. Never invent or infer unstated facts.
2. If billing information is absent or ambiguous, set billing_model to "unknown".
3. Australian Medicare Nuance:
   - "Bulk billing" means ALL patients are bulk billed without out-of-pocket costs.
   - "Mixed billing" means some patients pay private gap fees, but certain groups (e.g. under 16s, pensioners, Health Care Card holders) are bulk billed.
   - "Private billing" means all consultations incur an out-of-pocket fee with no standard bulk billing.
4. Output must strictly conform to the required JSON schema.
"""

EXTRACTION_FEW_SHOTS = [
    {
        "input": "We are a private billing clinic, however children aged under 16 and pensioners with a valid concession card will be bulk billed on weekdays.",
        "output": {
            "billing_model": "mixed_billing",
            "billing_reasoning": "Standard patients pay private fees, but under 16s and pensioners are bulk billed on weekdays.",
            "telehealth_available": False,
            "telehealth_caveat": None,
            "opening_hours_summary": None,
            "booking_platform": "unknown",
            "ai_confidence_score": 0.95
        }
    },
    {
        "input": "100% Bulk Billing practice for all Medicare card holders. Open Mon-Fri 8am to 6pm, Sat 9am to 1pm. Phone consults available for regular patients.",
        "output": {
            "billing_model": "bulk_billing",
            "billing_reasoning": "Advertised as 100% Bulk Billing practice for all Medicare card holders.",
            "telehealth_available": True,
            "telehealth_caveat": "Available for regular patients.",
            "opening_hours_summary": "Mon-Fri 08:00-18:00, Sat 09:00-13:00",
            "booking_platform": "unknown",
            "ai_confidence_score": 0.98
        }
    }
]

def build_enrichment_prompt(raw_billing: str, raw_hours: str, raw_cues: str) -> str:
    """Builds user prompt for LLM structured extraction."""
    return f"""Analyze the following raw practice snippets and extract structured signals:

RAW BILLING TEXT:
{raw_billing or 'Not provided'}

RAW OPENING HOURS TEXT:
{raw_hours or 'Not provided'}

RAW BOOKING/SERVICE CUES:
{raw_cues or 'Not provided'}

Return a valid JSON object matching the AIEnrichmentOutput schema.
"""
