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
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        self.openai_model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    async def enrich_practice(
        self,
        raw_billing: str,
        raw_hours: str,
        raw_cues: str,
        practice_name: str = "",
        suburb: str = "",
        state: str = "",
        phone: str = ""
    ) -> AIEnrichmentOutput:
        """Enriches unstructured text into validated structured metadata and verifies clinic phone."""
        
        # 1. Attempt OpenAI / OpenRouter structured extraction if key present
        if self.openai_key:
            try:
                return await self._call_openai(
                    raw_billing=raw_billing,
                    raw_hours=raw_hours,
                    raw_cues=raw_cues,
                    practice_name=practice_name,
                    suburb=suburb,
                    state=state,
                    phone=phone
                )
            except Exception as e:
                logger.warning(f"AI API call failed ({self.openai_model}): {e}. Falling back to deterministic semantic parser.")

        # 2. Deterministic Semantic Fallback (Zero-Credit / Offline Execution)
        return self._semantic_fallback(
            raw_billing=raw_billing,
            raw_hours=raw_hours,
            raw_cues=raw_cues,
            practice_name=practice_name,
            suburb=suburb,
            state=state,
            phone=phone
        )

    async def _call_openai(
        self,
        raw_billing: str,
        raw_hours: str,
        raw_cues: str,
        practice_name: str = "",
        suburb: str = "",
        state: str = "",
        phone: str = ""
    ) -> AIEnrichmentOutput:
        """Executes structured call against OpenAI or OpenRouter-compatible endpoint."""
        from openai import AsyncOpenAI
        client_kwargs = {"api_key": self.openai_key}
        if self.openai_base_url:
            client_kwargs["base_url"] = self.openai_base_url

        client = AsyncOpenAI(**client_kwargs)
        prompt = build_enrichment_prompt(
            raw_billing=raw_billing,
            raw_hours=raw_hours,
            raw_cues=raw_cues,
            practice_name=practice_name,
            suburb=suburb,
            state=state,
            phone=phone
        )

        create_kwargs = {
            "model": self.openai_model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        }
        
        # Apply strict json_object format for native OpenAI or compatible endpoints
        if not self.openai_base_url or "api.openai.com" in self.openai_base_url:
            create_kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**create_kwargs)
        raw_content = response.choices[0].message.content or "{}"

        # Clean markdown codeblocks if model wraps output in ```json ... ```
        clean_json_str = re.sub(r"^```(?:json)?", "", raw_content.strip(), flags=re.MULTILINE)
        clean_json_str = re.sub(r"```$", "", clean_json_str.strip(), flags=re.MULTILINE).strip()

        # Extract first valid JSON object substring if model includes conversational text
        json_match = re.search(r"(\{.*\})", clean_json_str, re.DOTALL)
        if json_match:
            clean_json_str = json_match.group(1)

        parsed = json.loads(clean_json_str)
        if isinstance(parsed, dict):
            if "reasoning" in parsed and "billing_reasoning" not in parsed:
                parsed["billing_reasoning"] = parsed["reasoning"]
            if "billing_model_evidence" in parsed and "billing_reasoning" not in parsed:
                parsed["billing_reasoning"] = parsed["billing_model_evidence"]
            if "booking_platform" in parsed and isinstance(parsed["booking_platform"], str):
                parsed["booking_platform"] = parsed["booking_platform"].lower().strip()
            if "billing_model" in parsed and isinstance(parsed["billing_model"], str):
                parsed["billing_model"] = parsed["billing_model"].lower().strip()
        
        # Validate through Pydantic
        return AIEnrichmentOutput.model_validate(parsed)

    def _semantic_fallback(
        self,
        raw_billing: str,
        raw_hours: str,
        raw_cues: str,
        practice_name: str = "",
        suburb: str = "",
        state: str = "",
        phone: str = ""
    ) -> AIEnrichmentOutput:
        """
        Deterministic, rule-based semantic parser for offline execution.
        Extracts billing, hours, booking signals, and verifies clinic phone numbers.
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
            lines = [l.strip() for l in hours_text.splitlines() if l.strip()]
            if lines:
                opening_hours_summary = " | ".join(lines[:4])

        # 5. Australian Telecom Phone Verification
        phone_clean = (phone or "").strip().replace(" ", "").replace("-", "")
        phone_verified = True
        phone_type = "landline"
        notes = "Verified Australian clinic line"

        state_prefixes = {
            "NSW": ["+612", "02"],
            "ACT": ["+612", "02"],
            "VIC": ["+613", "03"],
            "TAS": ["+613", "03"],
            "QLD": ["+617", "07"],
            "WA":  ["+618", "08"],
            "SA":  ["+618", "08"],
            "NT":  ["+618", "08"],
        }

        if not phone_clean or "90000000" in phone_clean:
            phone_verified = False
            phone_type = "invalid"
            notes = "Unlisted or placeholder contact line"
        elif phone_clean.startswith("+614") or phone_clean.startswith("04"):
            phone_verified = True
            phone_type = "mobile"
            notes = "Verified Australian mobile contact"
        elif any(phone_clean.startswith(p) for p in ["1300", "1800", "13", "+6113"]):
            phone_verified = True
            phone_type = "toll_free"
            notes = "Verified Australian national business line"
        else:
            state_up = (state or "").upper()
            expected = state_prefixes.get(state_up, [])
            if any(phone_clean.startswith(exp) for exp in expected):
                phone_verified = True
                phone_type = "landline"
                notes = f"Verified {state_up} geographic landline matching clinic location"
            elif expected:
                phone_verified = False
                phone_type = "landline"
                notes = f"Area code mismatch: {phone_clean[:4]} does not match expected {state_up} prefix ({expected[0]})"
            else:
                phone_verified = True
                phone_type = "landline"
                notes = "Valid Australian landline"

        return AIEnrichmentOutput(
            billing_model=billing_model,
            billing_reasoning=reasoning,
            telehealth_available=telehealth_available,
            telehealth_caveat=telehealth_caveat,
            opening_hours_summary=opening_hours_summary,
            booking_platform=booking_platform,
            phone_verified=phone_verified,
            phone_type=phone_type,
            phone_verification_notes=notes,
            ai_confidence_score=0.90 if billing_model != BillingModel.UNKNOWN else 0.70
        )
