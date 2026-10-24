from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re

class BillingModel(str, Enum):
    BULK_BILLING = "bulk_billing"
    MIXED_BILLING = "mixed_billing"
    PRIVATE_BILLING = "private_billing"
    UNKNOWN = "unknown"

class BookingPlatform(str, Enum):
    HOTDOC = "hotdoc"
    HEALTHENGINE = "healthengine"
    AUTOMED = "automed"
    PHONE_ONLY = "phone_only"
    OTHER_ONLINE = "other_online"
    UNKNOWN = "unknown"

class RawPracticePayload(BaseModel):
    """Raw unparsed DOM payload extracted from a practice page."""
    source_url: str
    suburb: str
    state: str
    practice_name_raw: Optional[str] = None
    address_raw: Optional[str] = None
    phone_raw: Optional[str] = None
    website_raw: Optional[str] = None
    directory_billing_tag_raw: Optional[str] = None
    opening_hours_raw: Optional[str] = None
    wheelchair_badge_raw: Optional[str] = None
    booking_cues_raw: Optional[str] = None
    extracted_at_utc: str

class AIEnrichmentOutput(BaseModel):
    """Strict schema for LLM structured output."""
    billing_model: BillingModel = BillingModel.UNKNOWN
    billing_reasoning: str = Field(..., description="Verbatim or grounded rationale from source text")
    telehealth_available: bool = False
    telehealth_caveat: Optional[str] = None
    opening_hours_summary: Optional[str] = None
    booking_platform: BookingPlatform = BookingPlatform.UNKNOWN
    ai_confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)

class ValidatedPracticeRecord(BaseModel):
    """
    Legally and ethically conservative schema for Australian GP practice intelligence.
    Focuses strictly on business/practice entities; excludes personal doctor information.
    """
    # 1. Practice Entity Identifiers (Business Information)
    practice_id: str = Field(..., description="Deterministic SHA256 composite key (normalized_name + postcode)")
    practice_name: str = Field(..., min_length=2, description="Commercial trading name of the clinic")
    practice_address: str = Field(..., min_length=5, description="Physical commercial street address")
    suburb: str = Field(..., min_length=2, description="Normalized suburb name")
    state: str = Field(..., description="Australian State or Territory")
    postcode: str = Field(..., description="4-digit Australian postal code")
    phone_main: str = Field(..., description="Normalized Australian phone (E.164: +61...)")
    website_url: Optional[str] = Field(None, description="Official public website link")

    # 2. Operational & Service Signals (Deterministic + AI)
    billing_model: BillingModel = Field(default=BillingModel.UNKNOWN)
    billing_model_evidence: Optional[str] = None
    telehealth_available: bool = Field(default=False)
    wheelchair_accessible: bool = Field(default=False)
    opening_hours_summary: Optional[str] = None
    booking_platform: BookingPlatform = Field(default=BookingPlatform.UNKNOWN)

    # 3. Growth Intelligence Metrics (Derived)
    opportunity_score: float = Field(..., ge=0.0, le=100.0, description="Calculated B2B fit score")
    growth_outreach_hook: Optional[str] = None

    # 4. Governance & Provenance Metadata
    source_url: str = Field(..., description="Canonical source URL")
    collected_at_utc: str = Field(..., description="ISO-8601 UTC timestamp")
    ai_confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    validation_status: str = Field(default="VALIDATED")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        clean = v.strip().upper()
        valid = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
        if clean not in valid:
            raise ValueError(f"Invalid Australian state: {v}. Must be one of {valid}")
        return clean

    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, v: str) -> str:
        clean = re.sub(r"\D", "", v.strip())
        if not re.match(r"^\d{4}$", clean):
            raise ValueError(f"Invalid Australian postcode: {v}. Must be exactly 4 digits.")
        return clean
