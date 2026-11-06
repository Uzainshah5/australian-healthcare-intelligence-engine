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
            "phone_verified": True,
            "phone_type": "landline",
            "phone_verification_notes": "Geographically verified landline.",
            "ai_confidence_score": 0.95
        }
    }
]

def build_enrichment_prompt(
    raw_billing: str,
    raw_hours: str,
    raw_cues: str,
    practice_name: str = "",
    suburb: str = "",
    state: str = "",
    phone: str = ""
) -> str:
    """Builds user prompt for LLM structured extraction and phone verification."""
    return f"""Analyze the following Australian GP clinic profile and verify all signals:

CLINIC IDENTITY:
- Name: {practice_name or 'Not specified'}
- Location: {suburb or 'Unknown'}, {state or 'Australia'}
- Extracted Phone: {phone or 'Not provided'}

RAW BILLING TEXT:
{raw_billing or 'Not provided'}

RAW OPENING HOURS TEXT:
{raw_hours or 'Not provided'}

RAW BOOKING/SERVICE CUES:
{raw_cues or 'Not provided'}

Perform phone verification (validating Australian telecom numbering plan, geographic area code match for {state}, and business line status).
Return a valid JSON object matching the AIEnrichmentOutput schema.
"""
