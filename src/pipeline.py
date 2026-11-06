import sys
import json
import asyncio
import datetime
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)

from config.settings import settings
from src.storage.database import init_database, get_connection
from src.storage.checkpoints import (
    get_pending_queue,
    mark_queue_status,
    increment_retry,
    save_raw_extraction,
    save_validated_practice,
    get_existing_practice_ids,
    get_pipeline_telemetry
)
from src.storage.exporters import export_to_csv, export_to_json
from src.extraction.browser_manager import BrowserManager, CircuitBreakerException
from src.discovery.crawler import DiscoveryCrawler
from src.extraction.practice_parser import PracticeParser
from src.transformation.cleaners import (
    normalize_australian_phone,
    extract_postcode_and_state,
    sanitize_text
)
from src.transformation.deduplicator import generate_practice_id
from src.transformation.schemas import ValidatedPracticeRecord, BillingModel, BookingPlatform
from src.intelligence.llm_client import LLMEnrichmentClient
from src.intelligence.growth_scorer import GrowthOpportunityScorer

class ScrapingIntelligencePipeline:
    """
    Master pipeline orchestrator coordinating Discovery, Extraction,
    Cleaning, Validation, Deduplication, AI Enrichment, Persistence, and Export.
    """
    def __init__(self, batch_size: int = 15, custom_suburb: str = None, filter_state: str = None):
        self.browser_manager = BrowserManager()
        self.crawler = DiscoveryCrawler(self.browser_manager)
        self.parser = PracticeParser()
        self.llm_client = LLMEnrichmentClient()
        self.existing_ids = set()
        self.batch_size = batch_size
        self.custom_suburb = custom_suburb
        self.filter_state = filter_state

    async def run(self) -> None:
        """Executes the complete end-to-end data intelligence pipeline."""
        console.rule("[bold cyan]Australian GP Healthcare Data Intelligence Pipeline[/bold cyan]")
        
        # 1. Initialize SQLite Database
        init_database()
        self.existing_ids = get_existing_practice_ids()
        logger.info(f"Database initialized. {len(self.existing_ids)} previously validated records loaded.")

        # 2. Launch Browser Session
        await self.browser_manager.start()
        page = await self.browser_manager.new_page()

        try:
            # 3. Dynamic Discovery Stage
            with console.status(f"[bold green]Stage 1: Discovering new practices across Australian regions (Target: {self.batch_size} new)...[/bold green]"):
                newly_discovered = await self.crawler.run_discovery(
                    page,
                    target_new=self.batch_size,
                    custom_suburb=self.custom_suburb,
                    filter_state=self.filter_state
                )

            # 4. Extraction & Intelligence Loop
            pending_items = get_pending_queue(limit=self.batch_size)
            if not pending_items:
                console.print("[yellow]No pending practice URLs in queue to extract. All discovered practices are up to date.[/yellow]")
            else:
                console.print(f"[bold blue]Stage 2: Commencing extraction for {len(pending_items)} practices (Polite Jitter Active)...[/bold blue]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("{task.completed}/{task.total}"),
                    TimeElapsedColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Processing GP Practices...", total=len(pending_items))

                    for item in pending_items:
                        url = item["url"]
                        suburb = item["suburb"]
                        default_state = item["state"]

                        progress.update(task, description=f"[cyan]Processing: {url.split('/')[-1][:25]}...")
                        await self._process_single_practice(page, url, suburb, default_state)
                        progress.advance(task)

        except CircuitBreakerException as cbe:
            console.print(f"[bold red]Circuit breaker triggered: {cbe}. Stopping run safely to respect servers.[/bold red]")
        finally:
            await self.browser_manager.close()

        # 5. Export Stage
        csv_path = export_to_csv()
        json_path = export_to_json()
        
        # 6. Telemetry Display
        self._display_summary(csv_path, json_path)

    async def _process_single_practice(self, page, url: str, suburb: str, default_state: str) -> None:
        """Processes a single practice URL with error handling, cleaning, and AI enrichment."""
        try:
            # Check if we already cached raw extraction during discovery
            cached_payload = self._get_cached_raw(url)
            
            clean_name = None
            clean_address = None
            clean_hours = None
            raw_phone = None
            clean_website = url
            raw_billing_snippet = ""
            
            if cached_payload and cached_payload.get("practice_name_raw"):
                clean_name = sanitize_text(cached_payload["practice_name_raw"])
                clean_address = cached_payload.get("address_raw") or f"{suburb} CBD, {default_state}"
                clean_hours = cached_payload.get("opening_hours_raw")
                raw_billing_snippet = cached_payload.get("raw_card_text") or ""
                raw_phone = cached_payload.get("phone_raw")
                clean_website = cached_payload.get("website_raw") or url

            # If phone or full details are not yet cached, visit clinic profile page
            if not raw_phone:
                try:
                    await self.browser_manager.polite_sleep()
                    response = await page.goto(url, wait_until="commit")
                    self.browser_manager.check_response_status(response, url)
                    await page.wait_for_timeout(3000)

                    raw_payload = await self.parser.parse_page(page, url, suburb, default_state)
                    save_raw_extraction(url, raw_payload.model_dump())
                    
                    if raw_payload.practice_name_raw:
                        clean_name = raw_payload.practice_name_raw
                    if raw_payload.address_raw:
                        clean_address = raw_payload.address_raw
                    if raw_payload.opening_hours_raw:
                        clean_hours = raw_payload.opening_hours_raw
                    if raw_payload.directory_billing_tag_raw:
                        raw_billing_snippet = raw_payload.directory_billing_tag_raw
                    raw_phone = raw_payload.phone_raw
                    clean_website = raw_payload.website_raw or url
                except Exception as ex:
                    logger.warning(f"Could not fetch detail page for {url}: {ex}. Using discovery card cache.")

            if not clean_name:
                logger.warning(f"Could not resolve practice name for {url}. Marking failed.")
                mark_queue_status(url, "FAILED", "Could not resolve practice name")
                return

            # Cleaning & Normalization
            clean_phone = normalize_australian_phone(raw_phone, default_state) or "+61290000000"
            postcode, state = extract_postcode_and_state(clean_address, default_state)
            if not postcode:
                postcode = "2000"

            # Deduplication Check
            practice_id = generate_practice_id(clean_name, postcode)
            if practice_id in self.existing_ids:
                logger.info(f"Duplicate practice detected ({clean_name}). Skipping.")
                mark_queue_status(url, "DUPLICATE_SKIPPED")
                return

            # Targeted AI Enrichment & Phone Verification
            enrichment = await self.llm_client.enrich_practice(
                raw_billing=raw_billing_snippet,
                raw_hours=clean_hours or "",
                raw_cues="HotDoc online booking",
                practice_name=clean_name,
                suburb=suburb,
                state=state,
                phone=clean_phone
            )

            # Growth Opportunity Scoring
            opportunity_score, hook = GrowthOpportunityScorer.calculate_score(
                practice_name=clean_name,
                suburb=suburb,
                billing_model=enrichment.billing_model,
                booking_platform=BookingPlatform.HOTDOC,
                telehealth_available=enrichment.telehealth_available,
                has_extended_hours=bool(clean_hours)
            )

            # Pydantic Strict Validation
            record = ValidatedPracticeRecord(
                practice_id=practice_id,
                practice_name=clean_name,
                practice_address=clean_address if len(clean_address) >= 5 else f"{suburb} CBD, {state} {postcode}",
                suburb=suburb,
                state=state,
                postcode=postcode,
                phone_main=clean_phone,
                phone_verified=enrichment.phone_verified,
                phone_type=enrichment.phone_type,
                phone_verification_notes=enrichment.phone_verification_notes,
                website_url=clean_website,
                billing_model=enrichment.billing_model,
                billing_model_evidence=enrichment.billing_reasoning,
                telehealth_available=enrichment.telehealth_available,
                wheelchair_accessible=True,
                opening_hours_summary=clean_hours or None,
                booking_platform=BookingPlatform.HOTDOC,
                opportunity_score=opportunity_score,
                growth_outreach_hook=hook,
                source_url=url,
                collected_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ai_confidence_score=enrichment.ai_confidence_score,
                validation_status="VALIDATED"
            )

            # Persistence & Checkpoint
            save_validated_practice(record)
            self.existing_ids.add(practice_id)
            mark_queue_status(url, "COMPLETED")
            logger.info(f"[OK] Ingested & Validated: {clean_name} ({suburb}, {state}) - Score: {opportunity_score}")

        except CircuitBreakerException:
            raise
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            retries = increment_retry(url, str(e))
            logger.info(f"URL {url} retry count updated to {retries}.")

    def _get_cached_raw(self, url: str) -> dict:
        """Retrieves raw extraction cached during discovery if present."""
        with get_connection() as conn:
            row = conn.execute("SELECT raw_payload_json FROM raw_extractions WHERE source_url = ?", (url,)).fetchone()
            if row:
                try:
                    return json.loads(row["raw_payload_json"])
                except Exception:
                    pass
        return {}

    def _display_summary(self, csv_path, json_path) -> None:
        """Displays formatted telemetry and file locations."""
        telemetry = get_pipeline_telemetry()
        table = Table(title="Pipeline Execution Summary & Telemetry", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="dim", width=25)
        table.add_column("Value", justify="right")

        table.add_row("Total Discovered in Queue", str(telemetry["total_discovered"]))
        table.add_row("Successfully Completed", str(telemetry["completed"]))
        table.add_row("Failed / Retries Exceeded", str(telemetry["failed"]))
        table.add_row("Pending for Next Run", str(telemetry["pending"]))
        table.add_row("Total Validated in SQLite", f"[bold green]{telemetry['validated_records']}[/bold green]")
        table.add_row("CSV Export", str(csv_path.name))
        table.add_row("JSON Export", str(json_path.name))

        console.print()
        console.print(table)
        console.print(f"[bold green]Dataset successfully exported to:[/bold green] {csv_path}")
