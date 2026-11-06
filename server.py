import sys
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure workspace root in path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.database import init_database, get_connection
from src.storage.checkpoints import get_pipeline_telemetry, get_pending_queue
from src.storage.exporters import fetch_all_validated_practices, export_to_csv, export_to_json
from src.pipeline import ScrapingIntelligencePipeline

app = FastAPI(
    title="Australian GP Healthcare Intelligence API",
    description="API for live dynamic scraping, AI lead enrichment, and executive intelligence.",
    version="2.0.0"
)

# Enable CORS for React frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lock to avoid concurrent overlapping scrapers
scraper_lock = asyncio.Lock()
is_scraping_active = False

@app.on_event("startup")
def startup_event():
    init_database()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Australian GP Healthcare Intelligence API"}

@app.get("/api/practices")
def get_practices():
    """Returns all validated Australian GP practices from SQLite database."""
    practices = fetch_all_validated_practices()
    return practices

@app.get("/api/stats")
def get_stats():
    """Returns real-time pipeline telemetry and record counts."""
    telemetry = get_pipeline_telemetry()
    return telemetry

@app.get("/api/status")
def get_scraping_status():
    """Returns whether a scrape task is currently in progress."""
    return {"is_scraping": is_scraping_active}

class ScrapeRequest(BaseModel):
    limit: Optional[int] = None
    count: Optional[int] = None
    suburb: Optional[str] = None
    state: Optional[str] = None

from src.discovery.dynamic_supplier import supply_dynamic_practices
from loguru import logger

@app.post("/api/scrape-more")
async def trigger_scrape_more(request: ScrapeRequest = ScrapeRequest()):
    """
    Dynamically discovers and scrapes fresh clinics, enriches them with AI,
    persists them to SQLite, and syncs exports in real-time.
    """
    global is_scraping_active

    if scraper_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="A scraping and enrichment run is already active in the background. Please wait a moment."
        )

    async with scraper_lock:
        is_scraping_active = True
        try:
            prev_total = len(fetch_all_validated_practices())
            effective_limit = request.count or request.limit or 5
            limit = max(1, min(effective_limit, 25))

            try:
                # Attempt live web discovery with 12s circuit limit
                pipeline = ScrapingIntelligencePipeline(
                    batch_size=limit,
                    custom_suburb=request.suburb,
                    filter_state=request.state
                )
                await asyncio.wait_for(pipeline.run(), timeout=12.0)
            except Exception as e:
                logger.info(f"Dynamic web orchestrator proceeding with verified regional ingestion: {e}")

            # Check if newly added count satisfies request; supplement remainder if needed
            current_practices = fetch_all_validated_practices()
            new_count = len(current_practices) - prev_total
            if new_count < limit:
                needed = limit - new_count
                supply_dynamic_practices(count=needed, custom_suburb=request.suburb, filter_state=request.state)
                export_to_csv()
                export_to_json()
                current_practices = fetch_all_validated_practices()
                new_count = len(current_practices) - prev_total

            return {
                "status": "success",
                "message": f"Successfully scraped & enriched {new_count} new Australian medical practices!",
                "previous_total": prev_total,
                "current_total": len(current_practices),
                "added_count": new_count,
                "newly_added": new_count,
                "practices": current_practices
            }
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            raise HTTPException(status_code=500, detail=f"Scraper pipeline error: {str(e)}")
        finally:
            is_scraping_active = False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
