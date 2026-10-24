import json
from datetime import datetime
from typing import Optional, List, Dict, Set
from src.storage.database import get_connection
from src.transformation.schemas import ValidatedPracticeRecord

def add_to_discovery_queue(url: str, suburb: str, state: str) -> bool:
    """Inserts a discovered practice URL into the queue if not already present."""
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO discovery_queue (url, suburb, state, status)
                VALUES (?, ?, ?, 'PENDING')
                """,
                (url, suburb, state)
            )
            return True
        except Exception:
            return False

def get_pending_queue(limit: int = 100) -> List[Dict]:
    """Retrieves next pending practice URLs to scrape."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT url, suburb, state, retry_count
            FROM discovery_queue
            WHERE status = 'PENDING'
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

def mark_queue_status(url: str, status: str, error_message: Optional[str] = None) -> None:
    """Updates the status of a URL in the discovery queue."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE discovery_queue
            SET status = ?,
                processed_at_utc = CURRENT_TIMESTAMP,
                error_message = ?
            WHERE url = ?
            """,
            (status, error_message, url)
        )

def increment_retry(url: str, error_message: str) -> int:
    """Increments retry count for a URL; sets to FAILED if max retries exceeded."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT retry_count FROM discovery_queue WHERE url = ?", (url,)
        )
        row = cursor.fetchone()
        current_retries = row["retry_count"] if row else 0
        new_retries = current_retries + 1
        
        status = "PENDING" if new_retries < 2 else "FAILED"
        conn.execute(
            """
            UPDATE discovery_queue
            SET retry_count = ?,
                status = ?,
                error_message = ?
            WHERE url = ?
            """,
            (new_retries, status, error_message, url)
        )
        return new_retries

def save_raw_extraction(source_url: str, raw_payload: dict, http_status: int = 200) -> None:
    """Stores the raw extraction JSON payload for data lineage and provenance."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO raw_extractions (source_url, raw_payload_json, http_status)
            VALUES (?, ?, ?)
            """,
            (source_url, json.dumps(raw_payload, ensure_ascii=False), http_status)
        )

def save_validated_practice(record: ValidatedPracticeRecord) -> None:
    """Saves a fully validated, enriched practice record."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO practices_validated (
                practice_id, practice_name, practice_address, suburb, state, postcode,
                phone_main, website_url, billing_model, billing_model_evidence,
                telehealth_available, wheelchair_accessible, opening_hours_summary,
                booking_platform, opportunity_score, growth_outreach_hook,
                source_url, collected_at_utc, ai_confidence_score, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.practice_id,
                record.practice_name,
                record.practice_address,
                record.suburb,
                record.state,
                record.postcode,
                record.phone_main,
                record.website_url,
                record.billing_model.value,
                record.billing_model_evidence,
                1 if record.telehealth_available else 0,
                1 if record.wheelchair_accessible else 0,
                record.opening_hours_summary,
                record.booking_platform.value,
                record.opportunity_score,
                record.growth_outreach_hook,
                record.source_url,
                record.collected_at_utc,
                record.ai_confidence_score,
                record.validation_status
            )
        )

def get_existing_practice_ids() -> Set[str]:
    """Returns all practice IDs already validated in the database to prevent duplicate work."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT practice_id FROM practices_validated")
        return {row["practice_id"] for row in cursor.fetchall()}

def get_pipeline_telemetry() -> Dict:
    """Returns counts of discovered, pending, completed, and validated records."""
    with get_connection() as conn:
        discovered = conn.execute("SELECT COUNT(*) as c FROM discovery_queue").fetchone()["c"]
        completed = conn.execute("SELECT COUNT(*) as c FROM discovery_queue WHERE status = 'COMPLETED'").fetchone()["c"]
        failed = conn.execute("SELECT COUNT(*) as c FROM discovery_queue WHERE status = 'FAILED'").fetchone()["c"]
        pending = conn.execute("SELECT COUNT(*) as c FROM discovery_queue WHERE status = 'PENDING'").fetchone()["c"]
        validated = conn.execute("SELECT COUNT(*) as c FROM practices_validated").fetchone()["c"]
        
        return {
            "total_discovered": discovered,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "validated_records": validated
        }
