import pytest
from app.services.parser_service import parse_vitamin_profile_report
from app.services.report_router import route_report_parser


SAMPLE_VITAMIN_TEXT = """
VITAMIN & NUTRITION PROFILE
Investigation               Observed Value    Unit      Reference Interval
25-Hydroxy Vitamin D        18.5              ng/mL     30-100
Vitamin B12                 145               pg/mL     200-900
Folate                      12.0              ng/mL     3-17
Ferritin                    450               ng/mL     30-400
Serum Iron                  95                µg/dL     60-170
"""

SAMPLE_NORMAL_VITAMIN_TEXT = """
VITAMIN PROFILE
Vitamin D (25-OH) 45.0 ng/mL (30-100)
Vitamin B12 450 pg/mL (200-900)
Folic Acid 8.5 ng/mL (3-17)
Serum Ferritin 150 ng/mL (30-400)
Total Iron 110 µg/dL (60-170)
"""


def test_parse_complete_vitamin_report():
    parsed = parse_vitamin_profile_report(SAMPLE_VITAMIN_TEXT)
    assert parsed["report_type"] == "VITAMIN_PROFILE"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 5
    assert len(parsed["biomarkers_missing"]) == 0

    keys = [b["key"] for b in parsed["biomarkers"]]
    assert "vitamin_d" in keys
    assert "vitamin_b12" in keys
    assert "folate" in keys
    assert "ferritin" in keys
    assert "iron" in keys


def test_vitamin_d_extraction():
    text = "25-OH Vitamin D 18.5 ng/mL (30-100)"
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "vitamin_d"
    assert bm["value"] == 18.5
    assert bm["unit"] == "ng/mL"
    assert bm["status"] == "Low"


def test_vitamin_b12_extraction():
    text = "Vitamin B12 145 pg/mL (200-900)"
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "vitamin_b12"
    assert bm["value"] == 145.0
    assert bm["unit"] == "pg/mL"
    assert bm["status"] == "Low"


def test_folate_extraction():
    text = "Folate 12.0 ng/mL (3-17)"
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "folate"
    assert bm["value"] == 12.0
    assert bm["unit"] == "ng/mL"
    assert bm["status"] == "Normal"


def test_ferritin_extraction():
    text = "Serum Ferritin 450 ng/mL (30-400)"
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "ferritin"
    assert bm["value"] == 450.0
    assert bm["unit"] == "ng/mL"
    assert bm["status"] == "High"


def test_iron_extraction():
    text = "Serum Iron 95 ug/dL (60-170)"
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "iron"
    assert bm["value"] == 95.0
    assert bm["status"] == "Normal"


def test_low_vitamin_d_classification():
    text = "Vitamin D 15.0 ng/mL (30-100)"
    parsed = parse_vitamin_profile_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "Low"
    assert "below the lower" in bm["status_reason"]


def test_low_vitamin_b12_classification():
    text = "Cyanocobalamin 120 pg/mL (200-900)"
    parsed = parse_vitamin_profile_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "Low"
    assert "below the lower" in bm["status_reason"]


def test_high_ferritin_classification():
    text = "Ferritin 520 ng/mL (30-400)"
    parsed = parse_vitamin_profile_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "High"
    assert "above the upper" in bm["status_reason"]


def test_fallback_reference_ranges():
    # Report text with no reference ranges provided
    no_range_text = """
    25-OH Vitamin D 18.5 ng/mL
    Vitamin B12 145 pg/mL
    Ferritin 450 ng/mL
    """
    parsed = parse_vitamin_profile_report(no_range_text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    assert bm_map["vitamin_d"]["reference_range"] == "30-100"
    assert bm_map["vitamin_d"]["status"] == "Low"

    assert bm_map["vitamin_b12"]["reference_range"] == "200-900"
    assert bm_map["vitamin_b12"]["status"] == "Low"

    assert bm_map["ferritin"]["reference_range"] == "30-400"
    assert bm_map["ferritin"]["status"] == "High"


def test_categories_generation():
    parsed = parse_vitamin_profile_report(SAMPLE_VITAMIN_TEXT)
    cats = parsed["categories"]
    assert "vitamins" in cats
    assert "iron_storage" in cats

    assert "vitamin_d" in cats["vitamins"]
    assert "vitamin_b12" in cats["vitamins"]
    assert "folate" in cats["vitamins"]

    assert "ferritin" in cats["iron_storage"]
    assert "iron" in cats["iron_storage"]


def test_parser_confidence_calculation():
    parsed = parse_vitamin_profile_report(SAMPLE_VITAMIN_TEXT)
    conf = parsed["parser_confidence"]
    assert conf["coverage_percent"] == 100.0
    assert conf["matched_biomarkers"] == 5
    assert conf["expected_biomarkers"] == 5

    # Partial report (2 out of 5)
    partial_text = "Vitamin D 45 ng/mL\nVitamin B12 400 pg/mL"
    partial_parsed = parse_vitamin_profile_report(partial_text)
    p_conf = partial_parsed["parser_confidence"]
    assert p_conf["coverage_percent"] == 40.0
    assert p_conf["matched_biomarkers"] == 2
    assert p_conf["expected_biomarkers"] == 5


def test_router_dispatch_vitamin():
    parsed = route_report_parser("VITAMIN_PROFILE", SAMPLE_NORMAL_VITAMIN_TEXT)
    assert parsed["report_type"] == "VITAMIN_PROFILE"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 5
    assert parsed["status_summary"]["normal"] == 5
    assert parsed["status_summary"]["high"] == 0
    assert parsed["status_summary"]["low"] == 0
