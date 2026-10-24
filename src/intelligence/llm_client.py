import os
import json
import re
from loguru import logger
from src.transformation.schemas import AIEnrichmentOutput, BillingModel, BookingPlatform
from src.intelligence.prompts import SYSTEM_PROMPT, build_enrichment_prompt

class LLMEnrichmentClient:
    """
    Manages structured extraction via LLMs (OpenAI / Gemini) with an automatic
    deterministic semantic fallback when API keys are not provided.
    Guarantees that invalid outputs are caught and validated by Pydantic.
    """
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    async def enrich_practice(
        self,
        raw_billing: str,
        raw_hours: str,
        raw_cues: str
    ) -> AIEnrichmentOutput:
        """Enriches unstructured text into validated structured metadata."""
        
        # 1. Attempt OpenAI structured extraction if key present
        if self.openai_key:
            try:
                return await self._call_openai(raw_billing, raw_hours, raw_cues)
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}. Falling back to deterministic semantic parser.")

        # 2. Deterministic Semantic Fallback (Zero-Credit / Offline Execution)
        return self._semantic_fallback(raw_billing, raw_hours, raw_cues)

    async def _call_openai(self, raw_billing: str, raw_hours: str, raw_cues: str) -> AIEnrichmentOutput:
        """Executes structured JSON call against OpenAI."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.openai_key)
        prompt = build_enrichment_prompt(raw_billing, raw_hours, raw_cues)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        raw_json_str = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_json_str)
        # Validate through Pydantic
        return AIEnrichmentOutput.model_validate(parsed)

    def _semantic_fallback(
        self,
        raw_billing: str,
        raw_hours: str,
        raw_cues: str
    ) -> AIEnrichmentOutput:
        """
        Deterministic, rule-based semantic parser for offline execution.
        Extracts billing, hours, and booking signals using strict heuristics.
        """
        billing_text = (raw_billing or "").lower()
        hours_text = raw_hours or ""
        cues_text = (raw_cues or "").lower()

        # 1. Billing Model Analysis
        billing_model = BillingModel.UNKNOWN
        reasoning = "No clear billing policy detected in source text."

        if "mixed billing" in billing_text or ("bulk bill" in billing_text and "private" in billing_text):
            billing_model = BillingModel.MIXED_BILLING
            reasoning = "Identified mixed billing policy with both private gap fees and conditional bulk billing."
        elif "bulk bill" in billing_text and not any(k in billing_text for k in ["private", "gap", "fee apply"]):
            billing_model = BillingModel.BULK_BILLING
            reasoning = "Clinic openly indicates standard bulk billing."
        elif "private" in billing_text or "fees apply" in billing_text:
            billing_model = BillingModel.PRIVATE_BILLING
            reasoning = "Clinic explicitly states private fees apply."

        # 2. Telehealth Detection
        combined_text = f"{billing_text} {cues_text} {hours_text}".lower()
        telehealth_available = any(w in combined_text for w in ["telehealth", "phone consult", "video consult", "telephone appointment"])
        telehealth_caveat = "Standard telehealth consultation options detected." if telehealth_available else None

        # 3. Booking Platform Detection
        booking_platform = BookingPlatform.UNKNOWN
        if "hotdoc" in combined_text or "online booking widget" in cues_text:
            booking_platform = BookingPlatform.HOTDOC
        elif "healthengine" in combined_text:
            booking_platform = BookingPlatform.HEALTHENGINE
        elif "automed" in combined_text:
            booking_platform = BookingPlatform.AUTOMED
        elif "phone only" in combined_text or ("call to book" in combined_text and not telehealth_available):
            booking_platform = BookingPlatform.PHONE_ONLY

        # 4. Opening Hours Normalization
        opening_hours_summary = None
        if hours_text:
            # Clean up and compact lines
            lines = [l.strip() for l in hours_text.splitlines() if l.strip()]
            if lines:
                opening_hours_summary = " | ".join(lines[:4]) # Compact summary of core days

        return AIEnrichmentOutput(
            billing_model=billing_model,
            billing_reasoning=reasoning,
            telehealth_available=telehealth_available,
            telehealth_caveat=telehealth_caveat,
            opening_hours_summary=opening_hours_summary,
            booking_platform=booking_platform,
            ai_confidence_score=0.90 if billing_model != BillingModel.UNKNOWN else 0.70
        )
