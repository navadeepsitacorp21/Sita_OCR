import pytest
from app.services.parser_service import parse_vitamin_profile_report
from app.services.report_router import route_report_parser


SAMPLE_VITAMIN_TEXT = """
VITAMIN & NUTRITION PROFILE
Investigation               Observed Value    Unit      Reference Interval
25-Hydroxy Vitamin D        18.5              ng/mL     30-100
Vitamin B1                  2.1               ng/mL     0.5-4.0
Vitamin B2                  25.0              ng/mL     1.6-58.2
Vitamin B3                  4.5               ng/mL     0.3-9.8
Vitamin B5                  65.0              ng/mL     11-150
Vitamin B6                  28.0              ng/mL     5-50
Vitamin B7                  1.5               ng/mL     0.2-3.0
Vitamin B12                 145               pg/mL     200-900
Folate                      12.0              ng/mL     3-17
Ferritin                    450               ng/mL     30-400
Serum Iron                  95                µg/dL     60-170
"""

SAMPLE_NORMAL_VITAMIN_TEXT = """
VITAMIN PROFILE
Vitamin D (25-OH) 45.0 ng/mL (30-100)
Vitamin B1 2.0 ng/mL (0.5-4.0)
Vitamin B2 20.0 ng/mL (1.6-58.2)
Vitamin B3 5.0 ng/mL (0.3-9.8)
Vitamin B5 50.0 ng/mL (11-150)
Vitamin B6 25.0 ng/mL (5-50)
Vitamin B7 1.0 ng/mL (0.2-3.0)
Vitamin B12 450 pg/mL (200-900)
Folic Acid 8.5 ng/mL (3-17)
Serum Ferritin 150 ng/mL (30-400)
Total Iron 110 µg/dL (60-170)
"""


def test_parse_complete_vitamin_report():
    parsed = parse_vitamin_profile_report(SAMPLE_VITAMIN_TEXT)
    assert parsed["report_type"] == "VITAMIN_PROFILE"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 11
    assert len(parsed["biomarkers_missing"]) == 0

    keys = [b["key"] for b in parsed["biomarkers"]]
    assert "vitamin_d" in keys
    assert "vitamin_b1" in keys
    assert "vitamin_b2" in keys
    assert "vitamin_b3" in keys
    assert "vitamin_b5" in keys
    assert "vitamin_b6" in keys
    assert "vitamin_b7" in keys
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
    assert "vitamin_b1" in cats["vitamins"]
    assert "vitamin_b2" in cats["vitamins"]
    assert "vitamin_b3" in cats["vitamins"]
    assert "vitamin_b5" in cats["vitamins"]
    assert "vitamin_b6" in cats["vitamins"]
    assert "vitamin_b7" in cats["vitamins"]
    assert "vitamin_b12" in cats["vitamins"]
    assert "folate" in cats["vitamins"]

    assert "ferritin" in cats["iron_storage"]
    assert "iron" in cats["iron_storage"]


def test_parser_confidence_calculation():
    parsed = parse_vitamin_profile_report(SAMPLE_VITAMIN_TEXT)
    conf = parsed["parser_confidence"]
    assert conf["coverage_percent"] == 100.0
    assert conf["matched_biomarkers"] == 11
    assert conf["expected_biomarkers"] == 11

    # Partial report (2 out of 11)
    partial_text = "Vitamin D 45 ng/mL\nVitamin B12 400 pg/mL"
    partial_parsed = parse_vitamin_profile_report(partial_text)
    p_conf = partial_parsed["parser_confidence"]
    assert p_conf["coverage_percent"] == round((2 / 11) * 100, 1)
    assert p_conf["matched_biomarkers"] == 2
    assert p_conf["expected_biomarkers"] == 11


def test_router_dispatch_vitamin():
    parsed = route_report_parser("VITAMIN_PROFILE", SAMPLE_NORMAL_VITAMIN_TEXT)
    assert parsed["report_type"] == "VITAMIN_PROFILE"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 11
    assert parsed["status_summary"]["normal"] == 11
    assert parsed["status_summary"]["high"] == 0
    assert parsed["status_summary"]["low"] == 0


def test_thyrocare_b_complex_multi_line_report():
    text = """
    VITAMIN B1 / THIAMIN
    1.18
    ng/mL
    0.5-4.0

    VITAMIN B12
    243
    pg/mL
    211-911
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 2
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    assert "vitamin_b1" in bm_map
    assert bm_map["vitamin_b1"]["value"] == 1.18
    assert bm_map["vitamin_b1"]["unit"] == "ng/mL"
    assert bm_map["vitamin_b1"]["reference_range"] == "0.5-4.0"
    assert bm_map["vitamin_b1"]["status"] == "Normal"

    assert "vitamin_b12" in bm_map
    assert bm_map["vitamin_b12"]["value"] == 243.0
    assert bm_map["vitamin_b12"]["unit"] == "pg/mL"
    assert bm_map["vitamin_b12"]["reference_range"] == "211-911"
    assert bm_map["vitamin_b12"]["status"] == "Normal"


def test_folic_acid_multi_line():
    text = """
    VITAMIN B9 / FOLIC ACID
    0.40
    ng/mL
    0.2-20
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "folate"
    assert bm["value"] == 0.40
    assert bm["unit"] == "ng/mL"
    assert bm["reference_range"] == "0.2-20"
    assert bm["status"] == "Normal"


def test_vitamin_b6_upper_boundary():
    text = """
    VITAMIN B6 / P5P
    50
    ng/mL
    5-50
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "vitamin_b6"
    assert bm["value"] == 50.0
    assert bm["unit"] == "ng/mL"
    assert bm["reference_range"] == "5-50"
    assert bm["status"] == "Normal"

