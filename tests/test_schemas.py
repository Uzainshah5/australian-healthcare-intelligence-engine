import pytest
from pydantic import ValidationError
from src.transformation.schemas import ValidatedPracticeRecord, BillingModel, BookingPlatform
from src.transformation.deduplicator import generate_practice_id

def test_valid_practice_record():
    record = ValidatedPracticeRecord(
        practice_id="abc1234567890def",
        practice_name="Sydney Central Medical Centre",
        practice_address="Suite 1, 100 Market St, Sydney NSW 2000",
        suburb="Sydney",
        state="NSW",
        postcode="2000",
        phone_main="+61292001122",
        website_url="https://sydneycentralmedical.example.com.au",
        billing_model=BillingModel.MIXED_BILLING,
        billing_model_evidence="Bulk billing for children; private fees for adults",
        telehealth_available=True,
        wheelchair_accessible=True,
        opening_hours_summary="Mon-Fri 08:00-18:00",
        booking_platform=BookingPlatform.HOTDOC,
        opportunity_score=85.0,
        growth_outreach_hook="Hello Sydney Central team. Notice you operate mixed billing...",
        source_url="https://www.hotdoc.com.au/medical-centres/sydney-nsw-2000/sydney-central",
        collected_at_utc="2026-10-24T10:00:00Z",
        ai_confidence_score=0.95,
        validation_status="VALIDATED"
    )
    assert record.practice_name == "Sydney Central Medical Centre"
    assert record.state == "NSW"
    assert record.postcode == "2000"

def test_invalid_state_rejection():
    with pytest.raises(ValidationError) as exc_info:
        ValidatedPracticeRecord(
            practice_id="test",
            practice_name="Test Clinic",
            practice_address="123 Test St",
            suburb="Sydney",
            state="CALIFORNIA", # Invalid Australian state
            postcode="2000",
            phone_main="+61292001122",
            opportunity_score=50.0,
            source_url="https://example.com",
            collected_at_utc="2026-10-24T10:00:00Z"
        )
    assert "Invalid Australian state" in str(exc_info.value)

def test_invalid_postcode_rejection():
    with pytest.raises(ValidationError) as exc_info:
        ValidatedPracticeRecord(
            practice_id="test",
            practice_name="Test Clinic",
            practice_address="123 Test St",
            suburb="Sydney",
            state="NSW",
            postcode="123", # Invalid 3-digit postcode
            phone_main="+61292001122",
            opportunity_score=50.0,
            source_url="https://example.com",
            collected_at_utc="2026-10-24T10:00:00Z"
        )
    assert "Invalid Australian postcode" in str(exc_info.value)

def test_deterministic_deduplication_id():
    id1 = generate_practice_id("Sydney Doctors Pty Ltd", "2000")
    id2 = generate_practice_id("Sydney Doctors", "2000")
    assert id1 == id2
