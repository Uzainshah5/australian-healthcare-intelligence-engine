from typing import Tuple, Optional
from src.transformation.schemas import BillingModel, BookingPlatform

class GrowthOpportunityScorer:
    """
    Computes an objective B2B Opportunity Score (0-100) and generates an
    automated outreach hook for healthcare growth and automation campaigns.
    """
    @classmethod
    def calculate_score(
        cls,
        practice_name: str,
        suburb: str,
        billing_model: BillingModel,
        booking_platform: BookingPlatform,
        telehealth_available: bool,
        has_extended_hours: bool
    ) -> Tuple[float, str]:
        score = 40.0 # Baseline score

        # 1. Billing Model Signals
        if billing_model == BillingModel.MIXED_BILLING:
            score += 20.0
            billing_hook = "operating a mixed-billing model balancing private gap fees"
        elif billing_model == BillingModel.PRIVATE_BILLING:
            score += 15.0
            billing_hook = "operating a private-fee billing structure"
        elif billing_model == BillingModel.BULK_BILLING:
            score += 10.0
            billing_hook = "supporting high patient volumes with standard bulk billing"
        else:
            billing_hook = "serving the local community"

        # 2. Booking Technology Gap Signals
        if booking_platform in (BookingPlatform.PHONE_ONLY, BookingPlatform.UNKNOWN):
            score += 25.0
            tech_hook = "Notice you still rely heavily on phone-based appointment bookings; automating online patient intake could significantly reduce reception overhead."
        else:
            score += 10.0
            tech_hook = f"Given your active use of {booking_platform.value.title()}, implementing automated patient recall workflows could optimize your appointment utilization."

        # 3. Telehealth & Access Signals
        if not telehealth_available:
            score += 10.0

        if has_extended_hours:
            score += 5.0

        # Cap score between 0.0 and 100.0
        final_score = min(100.0, max(0.0, round(score, 1)))

        # 4. Generate Synthesized Outreach Hook
        hook = f"Hello {practice_name} team in {suburb}. {tech_hook} (Targeting practices {billing_hook})."

        return final_score, hook
