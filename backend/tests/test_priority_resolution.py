import pytest
from app.services.parser_service import parse_vitamin_profile_report, resolve_highest_priority_candidate
from app.utils.alias_resolver import resolve_biomarker_alias


def test_priority_resolution_vitamin_d_total_with_d2_and_d3():
    """
    Case 1: Vitamin D Total + D2 + D3 present together (e.g. Thyrocare panel).
    Expected:
    - Canonical 'vitamin_d' is assigned Vitamin D Total (12.17 ng/mL).
    - 'vitamin_d2' (1.15) and 'vitamin_d3' (11.02) are preserved as separate secondary biomarkers.
    """
    text = """
    THYROCARE TOTAL HEALTH PROFILE
    VITAMIN D TOTAL : 12.17 ng/mL (30-100)
    VITAMIN D2      : 1.15  ng/mL
    VITAMIN D3      : 11.02 ng/mL (30-100)
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["parse_status"] == "success"
    
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    
    assert "vitamin_d" in bm_map
    assert bm_map["vitamin_d"]["value"] == 12.17
    assert bm_map["vitamin_d"]["unit"] == "ng/mL"
    assert bm_map["vitamin_d"]["matched_alias"] == "vitamin d total"
    assert bm_map["vitamin_d"]["alias_priority"] == 100
    assert bm_map["vitamin_d"]["status"] == "Low"

    assert "vitamin_d2" in bm_map
    assert bm_map["vitamin_d2"]["value"] == 1.15
    assert bm_map["vitamin_d2"]["unit"] == "ng/mL"

    assert "vitamin_d3" in bm_map
    assert bm_map["vitamin_d3"]["value"] == 11.02
    assert bm_map["vitamin_d3"]["unit"] == "ng/mL"


def test_priority_resolution_only_vitamin_d3():
    """
    Case 2: Only Vitamin D3 is present in the report.
    Expected:
    - Canonical 'vitamin_d' receives fallback mapping with D3 value (28.4 ng/mL).
    - 'vitamin_d3' is also available.
    """
    text = """
    VITAMIN D3 (CHOLECALCIFEROL) : 28.4 ng/mL (30-100)
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert "vitamin_d" in bm_map
    assert bm_map["vitamin_d"]["value"] == 28.4
    assert bm_map["vitamin_d"]["status"] == "Low"


def test_priority_resolution_only_vitamin_d_total():
    """
    Case 3: Only Vitamin D Total is present.
    Expected:
    - 'vitamin_d' is 42.5 ng/mL (Normal).
    - 'vitamin_d2' and 'vitamin_d3' are not found.
    """
    text = """
    25-OH VITAMIN D TOTAL : 42.5 ng/mL (30-100)
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert "vitamin_d" in bm_map
    assert bm_map["vitamin_d"]["value"] == 42.5
    assert bm_map["vitamin_d"]["status"] == "Normal"
    assert "vitamin_d2" not in bm_map
    assert "vitamin_d3" not in bm_map


def test_priority_resolution_only_generic_vitamin_d():
    """
    Case 4: Only generic Vitamin D is present.
    Expected:
    - 'vitamin_d' is extracted as 35.0 ng/mL.
    """
    text = """
    Vitamin D : 35.0 ng/mL (30-100)
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert "vitamin_d" in bm_map
    assert bm_map["vitamin_d"]["value"] == 35.0
    assert bm_map["vitamin_d"]["status"] == "Normal"


def test_priority_resolution_duplicate_aliases():
    """
    Case 5: Duplicate aliases appearing across the report.
    Expected:
    - Highest priority / best candidate is cleanly resolved without duplicates.
    """
    candidates = [
        {
            "key": "vitamin_d",
            "alias_priority": 50,
            "ocr_confidence": 0.85,
            "value_source": "lookahead",
            "context_match": True,
            "value": 20.0
        },
        {
            "key": "vitamin_d",
            "alias_priority": 100,
            "ocr_confidence": 0.99,
            "value_source": "same_line",
            "context_match": True,
            "value": 38.5
        },
        {
            "key": "vitamin_d",
            "alias_priority": 80,
            "ocr_confidence": 0.95,
            "value_source": "same_line",
            "context_match": True,
            "value": 35.0
        }
    ]
    resolved = resolve_highest_priority_candidate(candidates)
    assert resolved is not None
    assert resolved["alias_priority"] == 100
    assert resolved["value"] == 38.5


def test_alias_resolver_priority_scoring():
    """
    Check AliasResolver returns correct alias_priority scores.
    """
    res_total = resolve_biomarker_alias("Vitamin D Total 25.0 ng/mL")
    assert res_total is not None
    assert res_total["canonical_key"] == "vitamin_d"
    assert res_total["alias_priority"] == 100

    res_d3 = resolve_biomarker_alias("Vitamin D3 22.0 ng/mL")
    assert res_d3 is not None
    assert res_d3["canonical_key"] == "vitamin_d3"
    assert res_d3["alias_priority"] == 50
