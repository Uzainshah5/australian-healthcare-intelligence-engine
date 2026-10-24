import re
from typing import Optional, Tuple

STATE_AREA_CODES = {
    "NSW": "2",
    "ACT": "2",
    "VIC": "3",
    "TAS": "3",
    "QLD": "7",
    "WA": "8",
    "SA": "8",
    "NT": "8"
}

def normalize_australian_phone(raw_phone: Optional[str], default_state: str = "NSW") -> Optional[str]:
    """
    Normalizes an Australian phone number into standard E.164 format (+61...).
    Handles landlines ((02) 9999 9999, 0299999999), mobiles (0412 345 678),
    and international prefixed numbers (+61 2 ...).
    """
    if not raw_phone:
        return None
        
    # Strip everything except digits and leading +
    digits = re.sub(r"[^\d+]", "", raw_phone.strip())
    
    # If starts with +61
    if digits.startswith("+61"):
        clean_num = digits[3:]
        # Remove leading zero if present after +61
        if clean_num.startswith("0"):
            clean_num = clean_num[1:]
        if len(clean_num) == 9:
            return f"+61{clean_num}"
            
    # Remove leading + if any left
    digits_only = re.sub(r"\D", "", digits)
    
    # Standard 10-digit number starting with 0 (e.g. 0291234567 or 0412345678)
    if len(digits_only) == 10 and digits_only.startswith("0"):
        return f"+61{digits_only[1:]}"
        
    # 9-digit number without leading 0 (e.g. 291234567 or 412345678)
    if len(digits_only) == 9 and digits_only[0] in "23478":
        return f"+61{digits_only}"
        
    # 8-digit local landline without area code (e.g. 91234567)
    if len(digits_only) == 8:
        area_code = STATE_AREA_CODES.get(default_state.upper(), "2")
        return f"+61{area_code}{digits_only}"
        
    # If doesn't match standard, return formatted with +61 if plausible
    if len(digits_only) >= 9 and len(digits_only) <= 11:
        if digits_only.startswith("61"):
            return f"+{digits_only}"
        return f"+61{digits_only}"
        
    return None

def extract_postcode_and_state(address_text: Optional[str], fallback_state: str = "NSW") -> Tuple[Optional[str], str]:
    """
    Extracts Australian 4-digit postcode and state from address text.
    Matches patterns like 'NSW 2000', 'New South Wales 2010', or standalone 4 digits at the end.
    """
    if not address_text:
        return None, fallback_state
        
    # Pattern 1: State code followed by 4 digits: (NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})
    match = re.search(r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b\s*,?\s*(\d{4})\b", address_text, re.IGNORECASE)
    if match:
        state = match.group(1).upper()
        postcode = match.group(2)
        return postcode, state
        
    # Pattern 2: 4-digit postcode at end or standalone
    match_postcode = re.search(r"\b(0[289]\d{2}|[1-9]\d{3})\b", address_text)
    postcode = match_postcode.group(1) if match_postcode else None
    
    # Detect state
    state = fallback_state
    for s in ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]:
        if re.search(rf"\b{s}\b", address_text, re.IGNORECASE):
            state = s
            break
            
    return postcode, state

def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Strips redundant whitespace, newlines, and HTML tags."""
    if not text:
        return None
    # Strip HTML tags if any
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None
