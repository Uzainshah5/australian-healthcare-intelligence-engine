import yaml
import re
from pathlib import Path
from urllib.parse import urljoin
from loguru import logger
from playwright.async_api import Page
from config.settings import settings
from src.extraction.browser_manager import BrowserManager
from src.storage.checkpoints import (
    add_to_discovery_queue,
    save_raw_extraction,
    get_pipeline_telemetry,
    get_crawled_suburbs,
    record_crawled_suburb
)

class DiscoveryCrawler:
    """
    Crawls geographic search pages across Australian suburbs to discover practice URLs
    and initial practice-level metadata, dynamically populating the SQLite queue.
    """
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager

    def load_geographies(self) -> list:
        """Loads target suburbs from target_geographies.yaml."""
        config_path = settings.config_dir / "target_geographies.yaml"
        if not config_path.exists():
            return []
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("regions", [])

    async def run_discovery(
        self,
        page: Page,
        target_new: int = 15,
        custom_suburb: str = None,
        filter_state: str = None
    ) -> int:
        """
        Executes dynamic discovery across uncrawled target suburbs.
        Discovers at least `target_new` fresh practice records per run.
        """
        logger.info(f"Initiating dynamic discovery session (Targeting {target_new} new clinics)...")
        regions = self.load_geographies()
        crawled_slugs = get_crawled_suburbs()
        
        # Build prioritized suburb list
        suburbs_to_crawl = []
        
        if custom_suburb:
            # Custom suburb passed by user (e.g. melbourne-VIC-3000 or Brisbane)
            suburb_clean = custom_suburb.strip()
            state_match = re.search(r"-(NSW|VIC|QLD|WA|SA|TAS|ACT)-\d{4}", suburb_clean, re.I)
            state_code = state_match.group(1).upper() if state_match else "NSW"
            suburbs_to_crawl.append({
                "name": suburb_clean.split("-")[0].replace("_", " ").title(),
                "suburb_slug": suburb_clean if "-" in suburb_clean else f"{suburb_clean.lower()}-{state_code}-2000",
                "state": state_code
            })
        else:
            # Gather all suburbs from regions
            for region in regions:
                state = region.get("state", "NSW")
                if filter_state and state.upper() != filter_state.upper():
                    continue
                for sub in region.get("suburbs", []):
                    suburbs_to_crawl.append({
                        "name": sub.get("name", "Sydney"),
                        "suburb_slug": sub.get("suburb_slug", f"{sub.get('name', 'sydney').lower()}-{state}-2000"),
                        "state": state
                    })
            
            # Prioritize suburbs that have NOT been crawled yet
            uncrawled = [s for s in suburbs_to_crawl if s["suburb_slug"] not in crawled_slugs]
            if uncrawled:
                suburbs_to_crawl = uncrawled
            else:
                logger.info("All configured suburbs have been visited at least once. Cycling through for new listings...")

        newly_enqueued = 0

        for sub in suburbs_to_crawl:
            suburb_name = sub["name"]
            suburb_slug = sub["suburb_slug"]
            state = sub["state"]
            search_url = f"{settings.base_url}/search?in={suburb_slug}&for=general-practice"

            logger.info(f"Discovering: {suburb_name}, {state} ({search_url})")

            try:
                await self.browser_manager.polite_sleep()
                response = await page.goto(search_url, wait_until="commit")
                self.browser_manager.check_response_status(response, search_url)

                # Wait for SPA cards to hydrate
                await page.wait_for_timeout(5000)

                # Extract practice cards
                discovered_items = await self._extract_cards_from_page(page)
                record_crawled_suburb(suburb_slug, suburb_name, state)
                logger.info(f"Discovered {len(discovered_items)} practice cards in {suburb_name}.")

                # Enqueue URLs
                for item in discovered_items:
                    full_url = item["url"]
                    raw_payload = {
                        "practice_name_raw": item["name"],
                        "address_raw": item["address"],
                        "opening_hours_raw": item["hours"],
                        "source_url": full_url,
                        "suburb": suburb_name,
                        "state": state,
                        "raw_card_text": item["raw_text"]
                    }
                    if add_to_discovery_queue(full_url, suburb_name, state):
                        save_raw_extraction(full_url, raw_payload)
                        newly_enqueued += 1

                if newly_enqueued >= target_new:
                    logger.info(f"Achieved target batch size (+{newly_enqueued} new practices enqueued). Proceeding to extraction.")
                    break

            except Exception as e:
                logger.warning(f"Error exploring {search_url}: {e}")
                continue

        logger.info(f"Discovery phase completed. {newly_enqueued} fresh records queued for extraction.")
        return newly_enqueued

    async def _extract_cards_from_page(self, page: Page) -> list:
        """
        Extracts canonical practice profile links and card text from search results.
        Strictly resolves practice-level entity names and filters out doctor names.
        """
        cards_data = await page.evaluate("""() => {
            const cards = document.querySelectorAll('.ProviderCard');
            const items = [];
            cards.forEach(card => {
                const link = card.querySelector('a.ProviderCard-wrapper');
                if (!link) return;
                const href = link.getAttribute('href') || '';
                const titleEl = card.querySelector('.ProviderCard-title');
                const titleText = titleEl ? titleEl.innerText.trim() : '';
                
                const lineEl = card.querySelector('.ProviderCard-line p');
                const lineText = lineEl ? lineEl.innerText.trim() : '';
                const cardFullText = card.innerText.trim();
                
                // Determine if this is an individual doctor card or a clinic card
                const hasDoctorPath = /\\/doctors\\/[^/]+$/.test(href);
                const isDoctorTitle = /^(Dr|A\\/Prof|Prof|Doctor)\\b/i.test(titleText);
                
                let practiceName = titleText;
                let address = lineText;
                
                if (hasDoctorPath || isDoctorTitle) {
                    if (lineText.includes(',')) {
                        practiceName = lineText.split(',')[0].trim();
                        address = lineText;
                    } else if (lineText) {
                        practiceName = lineText;
                    }
                }
                
                items.push({
                    href: href,
                    name: practiceName,
                    address: address,
                    full_text: cardFullText
                });
            });
            return items;
        }""")

        results = []
        seen = set()

        for c in cards_data:
            href = c.get("href") or ""
            name = c.get("name") or ""
            address = c.get("address") or ""
            full_text = c.get("full_text") or ""
            
            if not href or "login" in href or "book" in href or not name:
                continue
                
            # Match canonical clinic base URL: /medical-centres/[suburb-state-postcode]/[clinic-slug]
            match = re.search(r"(/medical-centres/[^/]+-[a-z]{2,3}-\d{4}/[^/]+)", href, re.IGNORECASE)
            if not match:
                continue
                
            clean_path = match.group(1).rstrip("/")
            parts = clean_path.split("/")
            if len(parts) >= 4:
                base_clinic_path = "/".join(parts[:4])
                full_url = urljoin(settings.base_url, base_clinic_path + "/doctors")
                
                if full_url in seen:
                    continue
                seen.add(full_url)
                
                hours = ""
                for line in full_text.splitlines():
                    if any(term in line.lower() for term in ["open", "closed", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]):
                        hours = line.strip()
                        break

                results.append({
                    "url": full_url,
                    "name": name,
                    "address": address,
                    "hours": hours,
                    "raw_text": full_text
                })

        return results

