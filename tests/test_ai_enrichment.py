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
