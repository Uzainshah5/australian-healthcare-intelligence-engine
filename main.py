import sys
import json
import asyncio
from pathlib import Path
from loguru import logger
from rich.console import Console

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.pipeline import ScrapingIntelligencePipeline
from src.storage.database import init_database
from src.storage.checkpoints import (
    add_to_discovery_queue,
    mark_queue_status,
    save_validated_practice
)
from src.storage.exporters import export_to_csv, export_to_json
from src.transformation.schemas import ValidatedPracticeRecord

console = Console(force_terminal=True, legacy_windows=False)

def setup_logging():
    """Configures Loguru for clean console output and persistent file logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        log_dir / "scraper.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8"
    )

def run_demo_mode():
    """Seeds database with synthetic demonstration records and generates exports."""
    console.rule("[bold cyan]Demo Mode: Loading Synthetic Evaluation Dataset[/bold cyan]")
    init_database()
    demo_file = Path("data/demo_data.json")
    if not demo_file.exists():
        console.print("[red]data/demo_data.json not found![/red]")
        return
        
    with open(demo_file, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        record = ValidatedPracticeRecord.model_validate(r)
        # Add to discovery queue first to satisfy foreign key constraint
        add_to_discovery_queue(record.source_url, record.suburb, record.state)
        mark_queue_status(record.source_url, "COMPLETED")
        save_validated_practice(record)
        console.print(f"[green][OK] Ingested & Validated:[/green] {record.practice_name} ({record.suburb}, {record.state}) - Score: [bold]{record.opportunity_score}[/bold]")

    csv_path = export_to_csv()
    json_path = export_to_json()
    console.print(f"\n[bold green][OK] Successfully exported demonstration files:[/bold green]")
    console.print(f"  - CSV: [cyan]{csv_path}[/cyan]")
    console.print(f"  - JSON: [cyan]{json_path}[/cyan]\n")

async def main():
    setup_logging()
    if len(sys.argv) > 1 and sys.argv[1] in ("--demo", "-d", "--mock"):
        run_demo_mode()
        return

    pipeline = ScrapingIntelligencePipeline()
    await pipeline.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user. State and checkpoints safely preserved in SQLite.")
        sys.exit(0)
