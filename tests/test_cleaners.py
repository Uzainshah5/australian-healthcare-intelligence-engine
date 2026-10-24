import pytest
from src.transformation.cleaners import (
    normalize_australian_phone,
    extract_postcode_and_state,
    sanitize_text
)

def test_normalize_australian_phone_landlines():
    assert normalize_australian_phone("(02) 9123 4567") == "+61291234567"
    assert normalize_australian_phone("0291234567") == "+61291234567"
    assert normalize_australian_phone("9123 4567", default_state="NSW") == "+61291234567"
    assert normalize_australian_phone("9123 4567", default_state="VIC") == "+61391234567"

def test_normalize_australian_phone_mobiles():
    assert normalize_australian_phone("0412 345 678") == "+61412345678"
    assert normalize_australian_phone("+61 412 345 678") == "+61412345678"
    assert normalize_australian_phone("0412345678") == "+61412345678"

def test_normalize_australian_phone_invalid():
    assert normalize_australian_phone("123") is None
    assert normalize_australian_phone("") is None
    assert normalize_australian_phone(None) is None

def test_extract_postcode_and_state():
    postcode, state = extract_postcode_and_state("123 George St, Sydney NSW 2000")
    assert postcode == "2000"
    assert state == "NSW"

    postcode, state = extract_postcode_and_state("45 Collins St, Melbourne VIC 3000")
    assert postcode == "3000"
    assert state == "VIC"

def test_sanitize_text():
    raw = "  <span>  Sydney   Family   Doctors  \n\t</span>  "
    assert sanitize_text(raw) == "Sydney Family Doctors"
    assert sanitize_text("") is None
