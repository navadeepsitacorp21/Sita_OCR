import pytest
from app.services.parser_service import parse_kidney_function_test_report
from app.services.report_router import route_report_parser


def test_complete_electrolyte_panel():
    text = """
    SERUM CALCIUM 9.2 mg/dL 8.8-10.6
    SERUM PHOSPHORUS 3.8 mg/dL 2.5-4.5
    SERUM MAGNESIUM 2.1 mg/dL 1.7-2.4
    SERUM CHLORIDE 102 mmol/L 98-107
    """
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 4
    for bm in parsed["biomarkers"]:
        assert bm["status"] == "Normal"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert bm_map["calcium"]["value"] == 9.2
    assert bm_map["calcium"]["unit"] == "mg/dL"
    assert bm_map["phosphorus"]["value"] == 3.8
    assert bm_map["phosphorus"]["unit"] == "mg/dL"
    assert bm_map["magnesium"]["value"] == 2.1
    assert bm_map["magnesium"]["unit"] == "mg/dL"
    assert bm_map["chloride"]["value"] == 102.0
    assert bm_map["chloride"]["unit"] == "mmol/L"


def test_high_phosphorus():
    text = "SERUM PHOSPHORUS 5.9 mg/dL 2.5-4.5"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "phosphorus"
    assert bm["value"] == 5.9
    assert bm["status"] == "High"


def test_low_calcium():
    text = "SERUM CALCIUM 8.0 mg/dL 8.8-10.6"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "calcium"
    assert bm["value"] == 8.0
    assert bm["status"] == "Low"


def test_low_magnesium():
    text = "SERUM MAGNESIUM 1.4 mg/dL 1.7-2.4"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "magnesium"
    assert bm["value"] == 1.4
    assert bm["status"] == "Low"


def test_high_chloride():
    text = "SERUM CHLORIDE 110 mmol/L 98-107"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "chloride"
    assert bm["value"] == 110.0
    assert bm["status"] == "High"


def test_ocr_alias_variations():
    text = """
    S CALCIUM 9.5
    PHOSPHATE 3.7
    CL 103
    MG 2.2
    """
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 4
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert bm_map["calcium"]["value"] == 9.5
    assert bm_map["calcium"]["matched_alias"] == "s calcium"
    assert bm_map["phosphorus"]["value"] == 3.7
    assert bm_map["phosphorus"]["matched_alias"] == "phosphate"
    assert bm_map["chloride"]["value"] == 103.0
    assert bm_map["chloride"]["matched_alias"] == "cl"
    assert bm_map["magnesium"]["value"] == 2.2
    assert bm_map["magnesium"]["matched_alias"] == "mg"


def test_fallback_reference_ranges():
    text = """
    SERUM CALCIUM 9.2 mg/dL
    SERUM PHOSPHORUS 3.8 mg/dL
    SERUM MAGNESIUM 2.1 mg/dL
    SERUM CHLORIDE 102 mmol/L
    """
    parsed = parse_kidney_function_test_report(text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert bm_map["calcium"]["reference_range"] in ["8.5-10.5", "8.8-10.6"]
    assert bm_map["calcium"]["reference_source"] == "fallback"
    assert bm_map["phosphorus"]["reference_range"] == "2.5-4.5"
    assert bm_map["phosphorus"]["reference_source"] == "fallback"
    assert bm_map["magnesium"]["reference_range"] == "1.7-2.4"
    assert bm_map["magnesium"]["reference_source"] == "fallback"
    assert bm_map["chloride"]["reference_range"] == "98-107"
    assert bm_map["chloride"]["reference_source"] == "fallback"


def test_category_mapping():
    text = """
    SERUM SODIUM 140 mmol/L 135-145
    SERUM POTASSIUM 4.2 mmol/L 3.5-5.1
    SERUM CALCIUM 9.2 mg/dL 8.8-10.6
    SERUM PHOSPHORUS 3.8 mg/dL 2.5-4.5
    SERUM MAGNESIUM 2.1 mg/dL 1.7-2.4
    SERUM CHLORIDE 102 mmol/L 98-107
    """
    parsed = parse_kidney_function_test_report(text)
    electrolytes = parsed["categories"]["electrolytes"]
    assert "sodium" in electrolytes
    assert "potassium" in electrolytes
    assert "calcium" in electrolytes
    assert "phosphorus" in electrolytes
    assert "magnesium" in electrolytes
    assert "chloride" in electrolytes


def test_labsmart_kft_report_verification():
    sample_labsmart_text = """
    KIDNEY FUNCTION TEST (KFT / RFT)
    BUN 10.27 mg/dL 7-20
    Blood Urea 22 mg/dL 15-40
    Creatinine 1.01 mg/dL 0.6-1.3
    EGFR L 50.32 ml/min/1.73m² >90
    EGFR CATEGORY G3a
    Calcium 9.2 mg/dL 8.8-10.6
    Potassium 3.6 mmol/L 3.5-5.1
    Sodium 138 mmol/L 135-145
    Uric Acid 4 mg/dL 3.5-7.2
    Urea / Creatinine Ratio 10.17 ratio 10-20
    """
    parsed = parse_kidney_function_test_report(sample_labsmart_text)
    assert parsed["biomarkers_found"] == 9
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    bun_bm = bm_map.get("bun") or bm_map.get("blood_urea_nitrogen")
    urea_bm = bm_map.get("serum_urea") or bm_map.get("blood_urea")
    assert bun_bm["value"] == 10.27
    assert urea_bm["value"] == 22.0
    assert bm_map["serum_creatinine"]["value"] == 1.01
    assert bm_map["egfr"]["value"] == 50.32
    assert bm_map["egfr"]["status"] == "Low"
    assert bm_map["calcium"]["value"] == 9.2
    assert bm_map["potassium"]["value"] == 3.6
    assert bm_map["sodium"]["value"] == 138.0
    assert bm_map["uric_acid"]["value"] == 4.0
    assert bm_map["urea_creatinine_ratio"]["value"] == 10.17

    assert parsed["status_summary"]["low"] == 1
    assert parsed["status_summary"]["normal"] == 8
    assert parsed["status_summary"]["high"] == 0
