import asyncio
import pytest
from src.transformation.schemas import BillingModel, BookingPlatform
from src.intelligence.llm_client import LLMEnrichmentClient
from src.intelligence.growth_scorer import GrowthOpportunityScorer

def test_semantic_fallback_mixed_billing():
    async def _run():
        client = LLMEnrichmentClient()
        enrichment = await client.enrich_practice(
            raw_billing="We operate a mixed billing clinic where pensioners are bulk billed.",
            raw_hours="Monday - Friday: 8:00 AM - 6:00 PM\nSaturday: 9:00 AM - 1:00 PM",
            raw_cues="Online booking widget detected"
        )
        assert enrichment.billing_model == BillingModel.MIXED_BILLING
        assert enrichment.booking_platform == BookingPlatform.HOTDOC
        assert "mixed billing" in enrichment.billing_reasoning.lower()
    asyncio.run(_run())

def test_semantic_fallback_bulk_billing():
    async def _run():
        client = LLMEnrichmentClient()
        enrichment = await client.enrich_practice(
            raw_billing="100% bulk billing medical centre for all eligible patients.",
            raw_hours="Mon-Fri 9am - 5pm",
            raw_cues=""
        )
        assert enrichment.billing_model == BillingModel.BULK_BILLING
    asyncio.run(_run())

def test_growth_opportunity_scorer():
    score, hook = GrowthOpportunityScorer.calculate_score(
        practice_name="Newtown Medical Care",
        suburb="Newtown",
        billing_model=BillingModel.MIXED_BILLING,
        booking_platform=BookingPlatform.PHONE_ONLY,
        telehealth_available=False,
        has_extended_hours=True
    )
    # 40 (base) + 20 (mixed) + 25 (phone only) + 10 (no telehealth) + 5 (extended) = 100
    assert score == 100.0
    assert "Newtown" in hook
    assert "phone" in hook.lower()

def test_phone_verification_matching_state():
    client = LLMEnrichmentClient()
    res = client._semantic_fallback(
        raw_billing="Private billing",
        raw_hours="9-5",
        raw_cues="",
        practice_name="Sydney Medical Practice",
        suburb="Sydney",
        state="NSW",
        phone="+61292001234"
    )
    assert res.phone_verified is True
    assert res.phone_type == "landline"
    assert "NSW" in res.phone_verification_notes

def test_phone_verification_mismatched_state():
    client = LLMEnrichmentClient()
    res = client._semantic_fallback(
        raw_billing="Bulk billing",
        raw_hours="9-5",
        raw_cues="",
        practice_name="Melbourne Health",
        suburb="Melbourne",
        state="VIC",
        phone="+61730001234"  # 07 is QLD, not VIC
    )
    assert res.phone_verified is False
    assert "Area code mismatch" in res.phone_verification_notes

def test_phone_verification_mobile_and_placeholder():
    client = LLMEnrichmentClient()
    mobile_res = client._semantic_fallback(
        raw_billing="", raw_hours="", raw_cues="",
        state="QLD", phone="+61412345678"
    )
    assert mobile_res.phone_verified is True
    assert mobile_res.phone_type == "mobile"

    placeholder_res = client._semantic_fallback(
        raw_billing="", raw_hours="", raw_cues="",
        state="NSW", phone="+61290000000"
    )
    assert placeholder_res.phone_verified is False
    assert placeholder_res.phone_type == "invalid"
