import sqlite3
from pathlib import Path
from config.settings import settings

def get_connection(db_path: Path = settings.db_path) -> sqlite3.Connection:
    """Returns a SQLite connection configured with WAL mode for safe concurrency."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_database(db_path: Path = settings.db_path) -> None:
    """Initializes the database schema if tables do not exist."""
    with get_connection(db_path) as conn:
        conn.executescript("""
        -- 1. Discovery Queue & State Checkpoints
        CREATE TABLE IF NOT EXISTS discovery_queue (
            url TEXT PRIMARY KEY,
            suburb TEXT NOT NULL,
            state TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'DUPLICATE_SKIPPED')),
            retry_count INTEGER DEFAULT 0,
            discovered_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at_utc TIMESTAMP,
            error_message TEXT
        );

        -- 2. Raw Extraction Log (Data Lineage & Provenance)
        CREATE TABLE IF NOT EXISTS raw_extractions (
            source_url TEXT PRIMARY KEY,
            raw_payload_json TEXT NOT NULL,
            http_status INTEGER NOT NULL,
            extracted_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(source_url) REFERENCES discovery_queue(url)
        );

        -- 3. Production Enriched & Validated Dataset
        CREATE TABLE IF NOT EXISTS practices_validated (
            practice_id TEXT PRIMARY KEY,
            practice_name TEXT NOT NULL,
            practice_address TEXT NOT NULL,
            suburb TEXT NOT NULL,
            state TEXT NOT NULL,
            postcode TEXT NOT NULL,
            phone_main TEXT NOT NULL,
            website_url TEXT,
            billing_model TEXT NOT NULL,
            billing_model_evidence TEXT,
            telehealth_available INTEGER NOT NULL,
            wheelchair_accessible INTEGER NOT NULL,
            opening_hours_summary TEXT,
            booking_platform TEXT NOT NULL,
            opportunity_score REAL NOT NULL,
            growth_outreach_hook TEXT,
            source_url TEXT NOT NULL,
            collected_at_utc TIMESTAMP NOT NULL,
            ai_confidence_score REAL NOT NULL,
            validation_status TEXT NOT NULL DEFAULT 'VALIDATED',
            FOREIGN KEY(source_url) REFERENCES discovery_queue(url)
        );

        CREATE INDEX IF NOT EXISTS idx_discovery_status ON discovery_queue(status);
        CREATE INDEX IF NOT EXISTS idx_practice_postcode ON practices_validated(postcode);
        """)
