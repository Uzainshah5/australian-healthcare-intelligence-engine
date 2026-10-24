import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Response
from loguru import logger
from config.settings import settings

class CircuitBreakerException(Exception):
    """Raised when an HTTP 429, 403, or anti-bot challenge is encountered."""
    pass

class BrowserManager:
    """
    Manages Playwright browser lifecycle with defensive politeness,
    stealth configuration, and immediate circuit-breaking on access restrictions.
    """
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> None:
        """Launches Chromium with realistic desktop parameters and stealth init script."""
        logger.info("Initializing Playwright Chromium browser session...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars"
            ]
        )
        self._context = await self._browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport_width, "height": settings.viewport_height},
            locale="en-AU",
            timezone_id="Australia/Sydney"
        )
        # Prevent automated browser fingerprint detection in Ember/SPA
        await self._context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

    async def new_page(self) -> Page:
        """Creates a fresh page with default timeout settings."""
        if not self._context:
            await self.start()
        page = await self._context.new_page()
        page.set_default_timeout(settings.page_timeout_ms)
        return page

    async def polite_sleep(self) -> None:
        """Enforces a randomized jitter delay between 2.5 and 4.5 seconds."""
        delay = random.uniform(settings.min_delay_seconds, settings.max_delay_seconds)
        logger.debug(f"Polite delay: sleeping for {delay:.2f}s...")
        await asyncio.sleep(delay)

    def check_response_status(self, response: Optional[Response], url: str) -> None:
        """
        Circuit-breaker check: Halts the entire scraper if access restrictions
        such as HTTP 429 (Too Many Requests) or 403 (Forbidden) are returned.
        """
        if not response:
            return

        status = response.status
        if status in (429, 403):
            logger.critical(
                f"[CIRCUIT BREAKER] Access restriction encountered on {url} (HTTP {status}). "
                "Halting scraper immediately to respect server restrictions."
            )
            raise CircuitBreakerException(f"HTTP {status} received on {url}")

    async def close(self) -> None:
        """Gracefully closes context and browser instances."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Playwright browser session closed gracefully.")
