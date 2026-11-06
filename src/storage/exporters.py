import csv
import json
from pathlib import Path
from typing import List, Dict
from src.storage.database import get_connection
from config.settings import settings

def fetch_all_validated_practices() -> List[Dict]:
    """Retrieves all validated practices as dictionaries."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM practices_validated ORDER BY suburb, practice_name")
        return [dict(row) for row in cursor.fetchall()]

def export_to_json(filepath: Path = settings.exports_dir / "practices_dataset.json") -> Path:
    """Exports validated practices to clean JSON format and updates React dashboard dataset."""
    data = fetch_all_validated_practices()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Keep React dashboard synchronously updated
    frontend_data_path = settings.project_root / "frontend" / "src" / "data" / "practices.json"
    if frontend_data_path.parent.exists():
        with open(frontend_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    return filepath

def export_to_csv(filepath: Path = settings.exports_dir / "practices_dataset.csv") -> Path:
    """Exports validated practices to flattened CSV format."""
    data = fetch_all_validated_practices()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if not data:
        # Create empty CSV with headers
        fieldnames = [
            "practice_id", "practice_name", "practice_address", "suburb", "state", "postcode",
            "phone_main", "phone_verified", "phone_type", "phone_verification_notes", "website_url", "billing_model", "billing_model_evidence",
            "telehealth_available", "wheelchair_accessible", "opening_hours_summary",
            "booking_platform", "opportunity_score", "growth_outreach_hook",
            "source_url", "collected_at_utc", "ai_confidence_score", "validation_status"
        ]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        return filepath
        
    fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    return filepath
