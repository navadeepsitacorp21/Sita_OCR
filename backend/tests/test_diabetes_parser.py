import pytest
from app.services.parser_service import parse_diabetes_profile_report
from app.services.report_router import route_report_parser

SAMPLE_DIABETES_OCR_TEXT = """
PATIENT LAB REPORT - DIABETES EVALUATION PROFILE

TEST NAME                   OBSERVED VALUE   UNIT          REFERENCE RANGE
Fasting Blood Sugar         128              mg/dL         70 - 99
Postprandial Blood Sugar    135              mg/dL         70 - 140
Random Blood Sugar          110              mg/dL         70 - 140
HbA1c                       6.8              %             4.0 - 5.6
Estimated Average Glucose   148              mg/dL         
"""


def test_diabetes_parser_complete():
    result = parse_diabetes_profile_report(SAMPLE_DIABETES_OCR_TEXT)
    assert result["report_type"] == "DIABETES_PROFILE"
    assert result["parser_version"] in ["1.0.0", "1.2.0"]
    assert result["parse_status"] == "success"
    assert len(result["biomarkers"]) == 5

    bm_map = {b["key"]: b for b in result["biomarkers"]}

    # Fasting Blood Sugar
    assert "fasting_blood_sugar" in bm_map
    assert bm_map["fasting_blood_sugar"]["value"] == 128.0
    assert bm_map["fasting_blood_sugar"]["status"] == "High"
    assert bm_map["fasting_blood_sugar"]["upper_limit"] == 99.0

    # Postprandial Blood Sugar
    assert "postprandial_blood_sugar" in bm_map
    assert bm_map["postprandial_blood_sugar"]["value"] == 135.0
    assert bm_map["postprandial_blood_sugar"]["status"] == "Normal"

    # Random Blood Sugar
    assert "random_blood_sugar" in bm_map
    assert bm_map["random_blood_sugar"]["value"] == 110.0
    assert bm_map["random_blood_sugar"]["status"] == "Normal"

    # HbA1c
    assert "hba1c" in bm_map
    assert bm_map["hba1c"]["value"] == 6.8
    assert bm_map["hba1c"]["status"] == "High"
    assert bm_map["hba1c"]["upper_limit"] == 5.6

    # eAG
    assert "estimated_average_glucose" in bm_map
    assert bm_map["estimated_average_glucose"]["value"] == 148.0


def test_diabetes_parser_categories_and_confidence():
    result = parse_diabetes_profile_report(SAMPLE_DIABETES_OCR_TEXT)
    assert "categories" in result
    cats = result["categories"]
    assert "fasting_blood_sugar" in cats["blood_glucose"]
    assert "postprandial_blood_sugar" in cats["blood_glucose"]
    assert "random_blood_sugar" in cats["blood_glucose"]
    assert "hba1c" in cats["long_term_control"]
    assert "estimated_average_glucose" in cats["long_term_control"]

    conf = result["parser_confidence"]
    assert conf["matched_biomarkers"] == 5
    assert conf["expected_biomarkers"] == 5
    assert conf["coverage_percent"] == 100.0


def test_diabetes_parser_fallback_reference_ranges():
    # Report with omitted reference ranges
    ocr_text = """
    Glucose Fasting 88 mg/dL
    PPBS 120 mg/dL
    HbA1c - Glycated Hemoglobin 5.2 %
    """
    result = parse_diabetes_profile_report(ocr_text)
    assert result["report_type"] == "DIABETES_PROFILE"
    bm_map = {b["key"]: b for b in result["biomarkers"]}

    assert bm_map["fasting_blood_sugar"]["value"] == 88.0
    assert bm_map["fasting_blood_sugar"]["reference_range"] == "70-99"
    assert bm_map["fasting_blood_sugar"]["status"] == "Normal"

    assert bm_map["postprandial_blood_sugar"]["value"] == 120.0
    assert bm_map["postprandial_blood_sugar"]["reference_range"] == "70-140"
    assert bm_map["postprandial_blood_sugar"]["status"] == "Normal"

    assert bm_map["hba1c"]["value"] == 5.2
    assert bm_map["hba1c"]["reference_range"] == "4.0-5.6"
    assert bm_map["hba1c"]["status"] == "Normal"


def test_report_router_diabetes_dispatch():
    text = "Fasting Glucose 105 mg/dL (70-99)\nHbA1c 6.0 % (4.0-5.6)"
    routed = route_report_parser("DIABETES_PROFILE", text)
    assert routed["report_type"] == "DIABETES_PROFILE"
    assert "biomarkers" in routed
    assert len(routed["biomarkers"]) == 2
