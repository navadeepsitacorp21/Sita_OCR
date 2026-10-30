import pytest
from app.services.parser_service import parse_thyroid_profile_report
from app.services.report_router import route_report_parser

SAMPLE_THYROID_OCR_TEXT = """
PATIENT LAB REPORT - THYROID FUNCTION TEST (TFT)

TEST NAME                   OBSERVED VALUE   UNIT          REFERENCE RANGE
TSH                         6.5              µIU/mL        0.4 - 4.0
Total T3                    120              ng/dL         80 - 200
Total T4                    7.5              µg/dL         5.0 - 12.0
Free T3                     3.1              pg/mL         2.0 - 4.4
Free T4                     0.6              ng/dL         0.8 - 1.8
"""


def test_thyroid_parser_complete():
    result = parse_thyroid_profile_report(SAMPLE_THYROID_OCR_TEXT)
    assert result["report_type"] == "THYROID_PROFILE"
    assert result["parser_version"] == "1.0.0"
    assert result["parse_status"] == "success"
    assert len(result["biomarkers"]) == 5

    bm_map = {b["key"]: b for b in result["biomarkers"]}

    # TSH
    assert "tsh" in bm_map
    assert bm_map["tsh"]["value"] == 6.5
    assert bm_map["tsh"]["status"] == "High"
    assert bm_map["tsh"]["upper_limit"] == 4.0

    # Total T3
    assert "t3_total" in bm_map
    assert bm_map["t3_total"]["value"] == 120.0
    assert bm_map["t3_total"]["status"] == "Normal"

    # Total T4
    assert "t4_total" in bm_map
    assert bm_map["t4_total"]["value"] == 7.5
    assert bm_map["t4_total"]["status"] == "Normal"

    # Free T3
    assert "free_t3" in bm_map
    assert bm_map["free_t3"]["value"] == 3.1
    assert bm_map["free_t3"]["status"] == "Normal"

    # Free T4
    assert "free_t4" in bm_map
    assert bm_map["free_t4"]["value"] == 0.6
    assert bm_map["free_t4"]["status"] == "Low"
    assert bm_map["free_t4"]["lower_limit"] == 0.8


def test_thyroid_parser_categories_and_confidence():
    result = parse_thyroid_profile_report(SAMPLE_THYROID_OCR_TEXT)
    assert "categories" in result
    cats = result["categories"]
    assert "tsh" in cats["pituitary_hormones"]
    assert "t3_total" in cats["thyroid_hormones"]
    assert "t4_total" in cats["thyroid_hormones"]
    assert "free_t3" in cats["thyroid_hormones"]
    assert "free_t4" in cats["thyroid_hormones"]

    conf = result["parser_confidence"]
    assert conf["matched_biomarkers"] == 5
    assert conf["expected_biomarkers"] == 5
    assert conf["coverage_percent"] == 100.0


def test_thyroid_parser_fallback_reference_ranges():
    # Report with omitted reference ranges
    ocr_text = """
    Ultrasensitive TSH 2.2 µIU/mL
    Free T4 (FT4) 1.2 ng/dL
    Total T3 140 ng/dL
    """
    result = parse_thyroid_profile_report(ocr_text)
    assert result["report_type"] == "THYROID_PROFILE"
    bm_map = {b["key"]: b for b in result["biomarkers"]}

    assert bm_map["tsh"]["value"] == 2.2
    assert bm_map["tsh"]["reference_range"] == "0.4-4.0"
    assert bm_map["tsh"]["status"] == "Normal"

    assert bm_map["free_t4"]["value"] == 1.2
    assert bm_map["free_t4"]["reference_range"] == "0.8-1.8"
    assert bm_map["free_t4"]["status"] == "Normal"

    assert bm_map["t3_total"]["value"] == 140.0
    assert bm_map["t3_total"]["reference_range"] == "80-200"
    assert bm_map["t3_total"]["status"] == "Normal"


def test_report_router_thyroid_dispatch():
    text = "TSH 1.8 µIU/mL (0.4-4.0)\nFree T4 1.1 ng/dL (0.8-1.8)"
    routed = route_report_parser("THYROID_PROFILE", text)
    assert routed["report_type"] == "THYROID_PROFILE"
    assert "biomarkers" in routed
    assert len(routed["biomarkers"]) == 2
