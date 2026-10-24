import re
import datetime
from typing import Optional
from playwright.async_api import Page
from loguru import logger
from src.transformation.schemas import RawPracticePayload
from src.transformation.cleaners import sanitize_text

class PracticeParser:
    """
    Deterministically parses practice-level business information from
    a clinic profile page. Explicitly skips doctor personal profiles,
    practitioner bios, staff photos, and patient reviews.
    """
    async def parse_page(self, page: Page, url: str, suburb: str, state: str) -> RawPracticePayload:
        """Extracts approved practice-level fields from the current page DOM."""
        
        # 1. Practice Name (usually in <h1>)
        practice_name_raw = None
        h1_el = page.locator("h1").first
        if await h1_el.count() > 0:
            candidate = sanitize_text(await h1_el.inner_text())
            # Guard: ensure we extract practice name, not a practitioner's personal name
            if candidate and not re.match(r"^(Dr|A/Prof|Prof|Doctor)\b", candidate, re.IGNORECASE):
                practice_name_raw = candidate

        if not practice_name_raw:
            # Fallback: check breadcrumb or header clinic link
            clinic_crumb = page.locator("nav a[href*='/medical-centres/']").last
            if await clinic_crumb.count() > 0:
                crumb_text = sanitize_text(await clinic_crumb.inner_text())
                if crumb_text and not re.match(r"^(Dr|A/Prof|Prof)\b", crumb_text, re.IGNORECASE):
                    practice_name_raw = crumb_text

        if not practice_name_raw:
            # Fallback from URL slug (e.g. crown-st-medical-centre -> Crown St Medical Centre)
            slug = url.rstrip("/").split("/")[-1]
            if slug and slug != "doctors":
                practice_name_raw = slug.replace("-", " ").title()


        # 2. Practice Address
        address_raw = None
        # Common selectors: address element, data-testid, or class containing address
        addr_locators = [
            "address",
            "[data-testid*='address']",
            "[class*='address']",
            "p:has-text('NSW'), p:has-text('VIC'), p:has-text('QLD')"
        ]
        for sel in addr_locators:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible():
                text = sanitize_text(await el.inner_text())
                if text and len(text) > 5 and any(char.isdigit() for char in text):
                    address_raw = text
                    break

        # 3. Phone Number (prefer tel: link)
        phone_raw = None
        tel_link = page.locator("a[href^='tel:']").first
        if await tel_link.count() > 0:
            phone_href = await tel_link.get_attribute("href")
            if phone_href:
                phone_raw = phone_href.replace("tel:", "").strip()
        if not phone_raw:
            # Fallback to text containing phone pattern
            phone_el = page.locator("text=/\\(?0[23478]\\)?\\s*\\d{4}\\s*\\d{4}/").first
            if await phone_el.count() > 0:
                phone_raw = sanitize_text(await phone_el.inner_text())

        # 4. External Website Link (exclude hotdoc/internal links)
        website_raw = None
        ext_links = await page.eval_on_selector_all(
            "a[href^='http']",
            """els => els.map(e => e.getAttribute('href')).filter(h => 
                h && !h.includes('hotdoc.com.au') && !h.includes('facebook') && 
                !h.includes('twitter') && !h.includes('instagram') && !h.includes('google.com/maps')
            )"""
        )
        if ext_links:
            # Take the first plausible practice website link
            website_raw = ext_links[0]

        # 5. Billing Model Tag
        billing_tag_raw = None
        billing_el = page.locator(
            "text=/Bulk\\s*Billing|Mixed\\s*Billing|Private\\s*Billing/i"
        ).first
        if await billing_el.count() > 0:
            billing_tag_raw = sanitize_text(await billing_el.inner_text())

        # 6. Opening Hours Container
        opening_hours_raw = None
        hours_el = page.locator(
            "[data-testid*='opening-hours'], [class*='opening-hours'], [class*='hours'], table:has-text('Monday')"
        ).first
        if await hours_el.count() > 0:
            opening_hours_raw = sanitize_text(await hours_el.inner_text())

        # 7. Wheelchair Accessibility
        wheelchair_raw = None
        has_wheelchair = await page.evaluate("""() => {
            const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
            return bodyText.includes('wheelchair') || bodyText.includes('accessible');
        }""")
        if has_wheelchair:
            wheelchair_raw = "Wheelchair Accessible"

        # 8. Booking System Cues
        booking_cues_raw = None
        book_btn = page.locator("button:has-text('Book'), a:has-text('Book')").first
        if await book_btn.count() > 0:
            booking_cues_raw = "Online booking widget detected"

        return RawPracticePayload(
            source_url=url,
            suburb=suburb,
            state=state,
            practice_name_raw=practice_name_raw,
            address_raw=address_raw,
            phone_raw=phone_raw,
            website_raw=website_raw,
            directory_billing_tag_raw=billing_tag_raw,
            opening_hours_raw=opening_hours_raw,
            wheelchair_badge_raw=wheelchair_raw,
            booking_cues_raw=booking_cues_raw,
            extracted_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
