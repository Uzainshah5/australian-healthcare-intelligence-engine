import hashlib
import re

def normalize_name_for_dedup(name: str) -> str:
    """
    Normalizes practice name to catch common variations
    e.g. 'Sydney Doctors Pty Ltd' vs 'Sydney Doctors'
    """
    clean = name.lower()
    # Strip legal entity suffixes
    clean = re.sub(r"\b(pty|ltd|limited|inc|incorporated)\b", "", clean)
    # Strip non-alphanumeric
    clean = re.sub(r"[^a-z0-9]", "", clean)
    return clean

def generate_practice_id(practice_name: str, postcode: str) -> str:
    """
    Generates a deterministic unique identifier for a GP practice
    based on normalized name and postal code.
    """
    norm_name = normalize_name_for_dedup(practice_name)
    clean_postcode = re.sub(r"\D", "", postcode.strip())
    raw_key = f"{norm_name}_{clean_postcode}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
