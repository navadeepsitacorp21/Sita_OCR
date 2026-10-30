import pytest
from app.services.parser_service import parse_lipid_profile_report
from app.services.report_router import route_report_parser

SAMPLE_LIPID_OCR_TEXT = """
PATIENT LAB REPORT - LIPID PROFILE

TEST NAME                   OBSERVED VALUE   UNIT          REFERENCE RANGE
Total Cholesterol           232              mg/dL         <200
HDL Cholesterol             38               mg/dL         >40
LDL Cholesterol             145              mg/dL         <100
VLDL Cholesterol            28               mg/dL         5 - 40
Triglycerides               140              mg/dL         <150
Non-HDL Cholesterol         194              mg/dL         <130
Cholesterol / HDL Ratio     6.1              ratio         3.0 - 5.0
"""


def test_lipid_parser_complete():
    result = parse_lipid_profile_report(SAMPLE_LIPID_OCR_TEXT)
    assert result["report_type"] == "LIPID_PROFILE"
    assert result["parser_version"] == "1.0.0"
    assert result["parse_status"] == "success"
    assert len(result["biomarkers"]) == 7

    bm_map = {b["key"]: b for b in result["biomarkers"]}

    # Total Cholesterol
    assert "total_cholesterol" in bm_map
    assert bm_map["total_cholesterol"]["value"] == 232.0
    assert bm_map["total_cholesterol"]["status"] == "High"
    assert bm_map["total_cholesterol"]["upper_limit"] == 200.0

    # HDL
    assert "hdl" in bm_map
    assert bm_map["hdl"]["value"] == 38.0
    assert bm_map["hdl"]["status"] == "Low"
    assert bm_map["hdl"]["lower_limit"] == 40.0

    # LDL
    assert "ldl" in bm_map
    assert bm_map["ldl"]["value"] == 145.0
    assert bm_map["ldl"]["status"] == "High"
    assert bm_map["ldl"]["upper_limit"] == 100.0

    # VLDL
    assert "vldl" in bm_map
    assert bm_map["vldl"]["value"] == 28.0
    assert bm_map["vldl"]["status"] == "Normal"

    # Triglycerides
    assert "triglycerides" in bm_map
    assert bm_map["triglycerides"]["value"] == 140.0
    assert bm_map["triglycerides"]["status"] == "Normal"

    # Non-HDL
    assert "non_hdl" in bm_map
    assert bm_map["non_hdl"]["value"] == 194.0
    assert bm_map["non_hdl"]["status"] == "High"

    # Ratio
    assert "cholesterol_hdl_ratio" in bm_map
    assert bm_map["cholesterol_hdl_ratio"]["value"] == 6.1
    assert bm_map["cholesterol_hdl_ratio"]["status"] == "High"


def test_lipid_parser_categories_and_confidence():
    result = parse_lipid_profile_report(SAMPLE_LIPID_OCR_TEXT)
    assert "categories" in result
    cats = result["categories"]
    assert "total_cholesterol" in cats["cholesterol"]
    assert "hdl" in cats["cholesterol"]
    assert "ldl" in cats["cholesterol"]
    assert "vldl" in cats["cholesterol"]
    assert "non_hdl" in cats["cholesterol"]
    assert "triglycerides" in cats["triglycerides"]
    assert "cholesterol_hdl_ratio" in cats["ratios"]

    conf = result["parser_confidence"]
    assert conf["matched_biomarkers"] == 7
    assert conf["expected_biomarkers"] == 7
    assert conf["coverage_percent"] == 100.0


def test_lipid_parser_fallback_reference_ranges():
    # Report without printed reference ranges
    ocr_text = """
    Serum Cholesterol 180 mg/dL
    HDL - Cholesterol 55 mg/dL
    Serum Triglycerides 120 mg/dL
    """
    result = parse_lipid_profile_report(ocr_text)
    assert result["report_type"] == "LIPID_PROFILE"
    bm_map = {b["key"]: b for b in result["biomarkers"]}

    assert bm_map["total_cholesterol"]["value"] == 180.0
    assert bm_map["total_cholesterol"]["reference_range"] == "<200"
    assert bm_map["total_cholesterol"]["status"] == "Normal"

    assert bm_map["hdl"]["value"] == 55.0
    assert bm_map["hdl"]["reference_range"] == ">40"
    assert bm_map["hdl"]["status"] == "Normal"


def test_report_router_lipid_dispatch():
    text = "Total Cholesterol 220 mg/dL (<200)\nHDL 45 mg/dL (>40)"
    routed = route_report_parser("LIPID_PROFILE", text)
    assert routed["report_type"] == "LIPID_PROFILE"
    assert "biomarkers" in routed
    assert len(routed["biomarkers"]) >= 2
