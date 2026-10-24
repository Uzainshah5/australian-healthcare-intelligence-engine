import yaml
import re
from pathlib import Path
from urllib.parse import urljoin
from loguru import logger
from playwright.async_api import Page
from config.settings import settings
from src.extraction.browser_manager import BrowserManager
from src.storage.checkpoints import add_to_discovery_queue, save_raw_extraction, get_pipeline_telemetry

class DiscoveryCrawler:
    """
    Crawls geographic search pages on HotDoc to discover practice URLs
    and initial practice-level metadata, populating the SQLite queue.
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

    async def run_discovery(self, page: Page) -> int:
        """
        Executes discovery across configured target suburbs.
        Returns total newly discovered practice records.
        """
        regions = self.load_geographies()
        current_stats = get_pipeline_telemetry()
        
        # Check if we already have sufficient discovered practices
        if current_stats["total_discovered"] >= settings.target_sample_size:
            logger.info(
                f"Discovery queue already contains {current_stats['total_discovered']} records. "
                "Skipping discovery phase."
            )
            return current_stats["total_discovered"]

        logger.info(f"Starting discovery crawl for target sample size: {settings.target_sample_size}...")

        for region in regions:
            state = region.get("state", "NSW")
            suburbs = region.get("suburbs", [])

            for sub in suburbs:
                suburb_name = sub.get("name", "Sydney")
                suburb_slug = sub.get("suburb_slug", f"{suburb_name.lower()}-{state}-2000")
                search_url = f"{settings.base_url}/search?in={suburb_slug}&for=general-practice"

                logger.info(f"Navigating to search page: {search_url} ({suburb_name}, {state})")
                
                try:
                    await self.browser_manager.polite_sleep()
                    response = await page.goto(search_url, wait_until="commit")
                    self.browser_manager.check_response_status(response, search_url)

                    # Wait 6 seconds for Ember SPA to hydrate practice cards
                    await page.wait_for_timeout(6000)

                    # Extract practice cards
                    discovered_items = await self._extract_cards_from_page(page)
                    logger.info(f"Discovered {len(discovered_items)} practice cards for {suburb_name}.")

                    # Enqueue URLs and cache raw card text
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
                            
                    telemetry = get_pipeline_telemetry()
                    if telemetry["total_discovered"] >= settings.target_sample_size:
                        logger.info(f"Reached target sample size ({telemetry['total_discovered']} records).")
                        return telemetry["total_discovered"]

                except Exception as e:
                    logger.warning(f"Error exploring {search_url}: {e}")
                    continue

        final_stats = get_pipeline_telemetry()
        logger.info(f"Discovery phase completed. Total records in queue: {final_stats['total_discovered']}.")
        return final_stats["total_discovered"]

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

