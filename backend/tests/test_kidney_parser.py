import pytest
from app.services.parser_service import parse_kidney_function_test_report
from app.services.report_router import route_report_parser


SAMPLE_KFT_TEXT = """
KIDNEY FUNCTION TEST (KFT / RFT)
Investigation               Observed Value    Unit              Reference Interval
Serum Creatinine            2.1               mg/dL             0.6-1.3
Blood Urea                  55                mg/dL             15-40
Blood Urea Nitrogen (BUN)   28                mg/dL             7-20
Uric Acid                   8.5               mg/dL             3.5-7.2
Estimated GFR (eGFR)        45                mL/min/1.73m²     >90
Urea / Creatinine Ratio     26.2              ratio             10-20
Serum Sodium                138               mmol/L            135-145
Serum Potassium             4.5               mmol/L            3.5-5.1
Serum Calcium               9.2               mg/dL             8.8-10.6
Serum Phosphorus            3.8               mg/dL             2.5-4.5
Serum Magnesium             2.1               mg/dL             1.7-2.4
Serum Chloride              102               mmol/L            98-107
Serum Bicarbonate           24                mmol/L            22-29
"""

SAMPLE_NORMAL_KFT_TEXT = """
RENAL PROFILE (KFT)
Creatinine 0.9 mg/dL (0.6-1.3)
Blood Urea 25 mg/dL (15-40)
BUN 12 mg/dL (7-20)
Uric Acid 5.0 mg/dL (3.5-7.2)
eGFR 105 mL/min/1.73m² (>90)
Urea/Creatinine Ratio 15 ratio (10-20)
Sodium 140 mmol/L (135-145)
Potassium 4.2 mmol/L (3.5-5.1)
"""


def test_parse_complete_kft_report():
    parsed = parse_kidney_function_test_report(SAMPLE_KFT_TEXT)
    assert parsed["report_type"] == "KIDNEY_FUNCTION_TEST"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] >= 12
    assert len(parsed["biomarkers_missing"]) == 0

    keys = [b["key"] for b in parsed["biomarkers"]]
    assert "serum_creatinine" in keys
    assert ("serum_urea" in keys or "blood_urea" in keys)
    assert ("bun" in keys or "blood_urea_nitrogen" in keys)
    assert "uric_acid" in keys
    assert "egfr" in keys
    assert "urea_creatinine_ratio" in keys
    assert "sodium" in keys
    assert "potassium" in keys
    assert "calcium" in keys
    assert "phosphorus" in keys
    assert "magnesium" in keys
    assert "chloride" in keys


def test_serum_creatinine_extraction():
    text = "Serum Creatinine 2.1 mg/dL (0.6-1.3)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "serum_creatinine"
    assert bm["value"] == 2.1
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "High"


def test_blood_urea_extraction():
    text = "Blood Urea 55 mg/dL (15-40)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] in ["serum_urea", "blood_urea"]
    assert bm["value"] == 55.0
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "High"


def test_bun_extraction():
    text = "Blood Urea Nitrogen (BUN) 28 mg/dL (7-20)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] in ["bun", "blood_urea_nitrogen"]
    assert bm["value"] == 28.0
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "High"


def test_uric_acid_extraction():
    text = "Uric Acid 8.5 mg/dL (3.5-7.2)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "uric_acid"
    assert bm["value"] == 8.5
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "High"


def test_egfr_extraction():
    text = "eGFR 45 mL/min/1.73m² (>90)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "egfr"
    assert bm["value"] == 45.0
    assert bm["status"] == "Low"


def test_sodium_extraction():
    text = "Serum Sodium 138 mmol/L (135-145)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "sodium"
    assert bm["value"] == 138.0
    assert bm["unit"] == "mmol/L"
    assert bm["status"] == "Normal"


def test_potassium_extraction():
    text = "Serum Potassium 4.5 mmol/L (3.5-5.1)"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "potassium"
    assert bm["value"] == 4.5
    assert bm["unit"] == "mmol/L"
    assert bm["status"] == "Normal"


def test_high_creatinine_classification():
    text = "Creatinine 1.8 mg/dL (0.6-1.3)"
    parsed = parse_kidney_function_test_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "High"
    assert "above the upper" in bm["status_reason"]


def test_low_egfr_classification():
    text = "eGFR 55 mL/min/1.73m2 (>90)"
    parsed = parse_kidney_function_test_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "Low"
    assert "below the lower" in bm["status_reason"]


def test_high_uric_acid_classification():
    text = "Uric Acid 9.2 mg/dL (3.5-7.2)"
    parsed = parse_kidney_function_test_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "High"
    assert "above the upper" in bm["status_reason"]


def test_fallback_reference_ranges():
    # Report text with no reference ranges provided
    no_range_text = """
    Serum Creatinine 2.1 mg/dL
    Blood Urea 55 mg/dL
    eGFR 45 mL/min/1.73m²
    """
    parsed = parse_kidney_function_test_report(no_range_text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    assert bm_map["serum_creatinine"]["reference_range"] == "0.6-1.3"
    assert bm_map["serum_creatinine"]["status"] == "High"

    urea_bm = bm_map.get("serum_urea") or bm_map.get("blood_urea")
    assert urea_bm["reference_range"] == "15-40"
    assert urea_bm["status"] == "High"

    assert bm_map["egfr"]["reference_range"] in [">90", ">=90"]
    assert bm_map["egfr"]["status"] == "Low"


def test_categories_generation():
    parsed = parse_kidney_function_test_report(SAMPLE_KFT_TEXT)
    cats = parsed["categories"]
    assert "kidney_filtration" in cats
    assert "kidney_function" in cats
    assert "metabolic_markers" in cats
    assert "electrolytes" in cats
    assert "ratios" in cats

    assert "serum_creatinine" in cats["kidney_filtration"]
    assert ("serum_urea" in cats["kidney_filtration"] or "blood_urea" in cats["kidney_filtration"])
    assert ("bun" in cats["kidney_filtration"] or "blood_urea_nitrogen" in cats["kidney_filtration"])

    assert "egfr" in cats["kidney_function"]
    assert "uric_acid" in cats["metabolic_markers"]

    assert "sodium" in cats["electrolytes"]
    assert "potassium" in cats["electrolytes"]

    assert "urea_creatinine_ratio" in cats["ratios"]


def test_parser_confidence_calculation():
    parsed = parse_kidney_function_test_report(SAMPLE_KFT_TEXT)
    conf = parsed["parser_confidence"]
    assert conf["coverage_percent"] >= 90.0
    assert conf["matched_biomarkers"] >= 12
    assert conf["expected_biomarkers"] == 12

    # Partial report (2 out of 12)
    partial_text = "Serum Creatinine 0.9 mg/dL\nBlood Urea 25 mg/dL"
    partial_parsed = parse_kidney_function_test_report(partial_text)
    p_conf = partial_parsed["parser_confidence"]
    assert p_conf["coverage_percent"] == round((2 / 12) * 100, 1)
    assert p_conf["matched_biomarkers"] == 2
    assert p_conf["expected_biomarkers"] == 12


def test_router_dispatch_kft():
    parsed = route_report_parser("KIDNEY_FUNCTION_TEST", SAMPLE_NORMAL_KFT_TEXT)
    assert parsed["report_type"] == "KIDNEY_FUNCTION_TEST"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 8
    assert parsed["status_summary"]["normal"] == 8
    assert parsed["status_summary"]["high"] == 0
    assert parsed["status_summary"]["low"] == 0


def test_egfr_extraction_with_category_line():
    text = """
    EGFR L 50.32 ml/min/1.73m² >90
    EGFR CATEGORY G3a
    """
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "egfr"
    assert bm["name"] in ["Estimated GFR (eGFR)", "Estimated Glomerular Filtration Rate (eGFR)"]
    assert bm["value"] == 50.32
    assert bm["unit"] == "mL/min/1.73m²"
    assert bm["reference_range"] in [">90", ">=90"]
    assert bm["status"] == "Low"
    assert bm["reference_source"] == "report"
    assert bm["matched_alias"] == "egfr"
    assert bm.get("ckd_stage") == "G3A"


def test_egfr_category_line_only_ignored():
    text = "EGFR CATEGORY G3a"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 0
    assert "egfr" in parsed["biomarkers_missing"]


def test_egfr_normal_value_with_category_line():
    text = "eGFR 95 ml/min/1.73m² >90"
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "egfr"
    assert bm["value"] == 95.0
    assert bm["status"] == "Normal"
    assert bm["reference_range"] == ">90"


