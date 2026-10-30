import pytest
from app.services.medical_explanation_engine import (
    generate_medical_explanation,
    generate_overall_explanation,
    generate_abnormal_findings_explanation,
    generate_biomarker_explanation,
    generate_pattern_explanation,
    generate_trend_explanation,
    generate_doctor_discussion_points,
    DISCLAIMER_TEXT,
)


def test_completely_normal_report():
    biomarkers = [
        {"key": "hemoglobin", "name": "Hemoglobin", "value": 14.5, "unit": "g/dL", "status": "Normal", "reference_range": "13 - 17"},
        {"key": "rbc_count", "name": "RBC Count", "value": 5.0, "unit": "10^6/uL", "status": "Normal", "reference_range": "4.5 - 5.5"},
        {"key": "wbc_count", "name": "WBC Count", "value": 6.8, "unit": "10^3/uL", "status": "Normal", "reference_range": "4 - 10"},
    ]
    res = generate_medical_explanation(report_type="CBC", biomarkers=biomarkers)

    assert "reassuring" in res["overall_explanation"].lower()
    assert "reference ranges" in res["overall_explanation"].lower()
    assert len(res["biomarker_explanations"]) == 0
    assert len(res["pattern_explanations"]) == 0
    assert "All measured parameters fall within standard" in res["key_findings"][0]
    assert len(res["doctor_discussion"]) >= 1
    assert res["disclaimer"] == DISCLAIMER_TEXT


def test_report_with_one_high_value():
    biomarkers = [
        {"key": "serum_urea", "name": "Serum Urea", "value": 25.0, "unit": "mg/dL", "status": "Normal", "reference_range": "15 - 40"},
        {"key": "serum_creatinine", "name": "Serum Creatinine", "value": 1.6, "unit": "mg/dL", "status": "High", "reference_range": "0.7 - 1.3"},
        {"key": "uric_acid", "name": "Uric Acid", "value": 5.0, "unit": "mg/dL", "status": "Normal", "reference_range": "3.5 - 7.2"},
    ]
    res = generate_medical_explanation(report_type="KFT", biomarkers=biomarkers)

    assert "Serum Creatinine" in res["overall_explanation"]
    assert "above" in res["overall_explanation"].lower()
    assert "remaining results are within range" in res["overall_explanation"].lower()

    assert len(res["biomarker_explanations"]) == 1
    bm_exp = res["biomarker_explanations"][0]
    assert bm_exp["biomarker"] == "Serum Creatinine"
    assert bm_exp["status"] == "high"
    assert "above the laboratory's reported range" in bm_exp["explanation"]
    # Verify non-diagnostic language
    assert "you have kidney disease" not in bm_exp["explanation"].lower()
    assert "can occur with" in bm_exp["explanation"].lower() or "elevated" in bm_exp["explanation"].lower()


def test_report_with_multiple_abnormalities():
    biomarkers = [
        {"key": "serum_creatinine", "name": "Serum Creatinine", "value": 1.5, "unit": "mg/dL", "status": "High", "reference_range": "0.7 - 1.3"},
        {"key": "phosphorus", "name": "Phosphorus", "value": 1.4, "unit": "mg/dL", "status": "Low", "reference_range": "2.4 - 5.1"},
        {"key": "serum_urea", "name": "Serum Urea", "value": 15.0, "unit": "mg/dL", "status": "Normal", "reference_range": "13 - 43"},
        {"key": "sodium", "name": "Sodium", "value": 139.0, "unit": "mmol/L", "status": "Normal", "reference_range": "136 - 145"},
    ]
    res = generate_medical_explanation(report_type="KFT", biomarkers=biomarkers)

    assert "Serum Creatinine is above" in res["overall_explanation"]
    assert "Phosphorus is below" in res["overall_explanation"]
    assert len(res["biomarker_explanations"]) == 2
    assert len(res["key_findings"]) == 2

    # Verify both elevated and low are clearly reported in key findings
    findings_str = " ".join(res["key_findings"])
    assert "Serum Creatinine is elevated" in findings_str
    assert "Phosphorus is below" in findings_str


def test_detected_pattern():
    patterns = [
        {
            "name": "Microcytic Hypochromic Indices",
            "summary": "Both MCV and MCH are below the provided reference ranges.",
            "educational_note": "When both MCV and MCH are low, red blood cells are smaller and contain less hemoglobin. This pattern is commonly associated with iron deficiency, hemoglobinopathies (such as thalassemia trait), or chronic inflammation.",
            "recommendation": "Discuss with your physician to correlate with total hemoglobin and iron studies."
        }
    ]
    p_exp = generate_pattern_explanation(patterns)
    assert len(p_exp) == 1
    assert p_exp[0]["pattern"] == "Microcytic Hypochromic Indices"
    assert "smaller and contain less hemoglobin" in p_exp[0]["explanation"]
    assert "iron deficiency" in p_exp[0]["explanation"]
    assert "Clinical consideration" in p_exp[0]["explanation"]


def test_trend_available():
    trends = {
        "serum_creatinine": {
            "name": "Serum Creatinine",
            "direction": "increased",
            "current_value": 1.5,
            "previous_value": 1.2,
            "unit": "mg/dL"
        }
    }
    t_exp = generate_trend_explanation(trends)
    assert "Serum Creatinine" in t_exp
    assert "increased" in t_exp
    assert "from 1.2 to 1.5 mg/dL" in t_exp


def test_multi_report_consistent_trend():
    trends = {
        "serum_creatinine": {
            "name": "Serum Creatinine",
            "direction": "increased",
            "current_value": 1.6,
            "previous_value": 1.4,
            "unit": "mg/dL",
            "multi_report_trend": "Serum Creatinine has consistently increased across the last 3 recorded reports."
        }
    }
    t_exp = generate_trend_explanation(trends)
    assert "consistently increased across the last 3 recorded reports" in t_exp


def test_no_trend_history():
    t_exp = generate_trend_explanation({})
    assert "not enough previous report data" in t_exp.lower()

    t_exp_none = generate_trend_explanation(None)
    assert "not enough previous report data" in t_exp_none.lower()


def test_needs_review_handling():
    biomarkers = [
        {
            "key": "alt_sgpt",
            "name": "ALT (SGPT)",
            "value": 40.0,
            "unit": "U/L",
            "status": "Needs Review",
            "status_reason": "Reference range could not be verified",
            "reference_range": "—"
        }
    ]
    res = generate_medical_explanation(report_type="LFT", biomarkers=biomarkers, patient_gender="male")
    assert len(res["biomarker_explanations"]) == 1
    bm_exp = res["biomarker_explanations"][0]
    assert bm_exp["status"] == "needs_review"
    assert "could not be confidently interpreted" in bm_exp["explanation"]


def test_missing_gender_reference_information():
    biomarkers = [
        {
            "key": "alt_sgpt",
            "name": "ALT (SGPT)",
            "value": 40.0,
            "unit": "U/L",
            "status": "Needs Review",
            "status_reason": "Gender required for gender-specific reference range",
            "reference_range": "Male: <45, Female: <35"
        }
    ]
    res = generate_medical_explanation(report_type="LFT", biomarkers=biomarkers, patient_gender=None)
    assert len(res["biomarker_explanations"]) == 1
    bm_exp = res["biomarker_explanations"][0]
    assert "gender-specific reference" in bm_exp["explanation"].lower()


def test_cbc_panel_explanation():
    biomarkers = [
        {"key": "hemoglobin", "name": "Hemoglobin", "value": 10.5, "unit": "g/dL", "status": "Low", "reference_range": "13 - 17"},
        {"key": "mcv", "name": "MCV", "value": 72.0, "unit": "fL", "status": "Low", "reference_range": "83 - 101"},
        {"key": "mch", "name": "MCH", "value": 24.0, "unit": "pg", "status": "Low", "reference_range": "27 - 32"},
        {"key": "platelet_count", "name": "Platelet Count", "value": 250.0, "unit": "10^3/uL", "status": "Normal", "reference_range": "150 - 410"},
    ]
    res = generate_medical_explanation(report_type="CBC", biomarkers=biomarkers)
    assert "CBC" in res["overall_explanation"]
    assert len(res["biomarker_explanations"]) == 3
    discussion_text = " ".join(res["doctor_discussion"]).lower()
    assert "red blood cell" in discussion_text or "indices" in discussion_text or "iron" in discussion_text


def test_lft_panel_explanation():
    biomarkers = [
        {"key": "alt_sgpt", "name": "ALT (SGPT)", "value": 75.0, "unit": "U/L", "status": "High", "reference_range": "10 - 40"},
        {"key": "ast_sgot", "name": "AST (SGOT)", "value": 68.0, "unit": "U/L", "status": "High", "reference_range": "10 - 35"},
        {"key": "total_bilirubin", "name": "Total Bilirubin", "value": 0.8, "unit": "mg/dL", "status": "Normal", "reference_range": "0.2 - 1.2"},
    ]
    res = generate_medical_explanation(report_type="LIVER_FUNCTION_TEST", biomarkers=biomarkers)
    assert "LFT" in res["overall_explanation"]
    assert "ALT" in res["overall_explanation"] and "AST" in res["overall_explanation"]
    discussion_text = " ".join(res["doctor_discussion"]).lower()
    assert "liver transaminase" in discussion_text or "medication" in discussion_text


def test_kft_panel_explanation():
    biomarkers = [
        {"key": "serum_creatinine", "name": "Serum Creatinine", "value": 1.5, "unit": "mg/dL", "status": "High", "reference_range": "0.7 - 1.3"},
        {"key": "serum_urea", "name": "Serum Urea", "value": 15.0, "unit": "mg/dL", "status": "Normal", "reference_range": "13 - 43"},
        {"key": "phosphorus", "name": "Phosphorus", "value": 1.4, "unit": "mg/dL", "status": "Low", "reference_range": "2.4 - 5.1"},
    ]
    res = generate_medical_explanation(report_type="KIDNEY_FUNCTION_TEST", biomarkers=biomarkers)
    assert "KFT" in res["overall_explanation"]
    assert "kidney-related" in res["overall_explanation"]
    discussion_text = " ".join(res["doctor_discussion"]).lower()
    assert "creatinine" in discussion_text
    assert "phosphorus" in discussion_text


def test_safety_and_non_diagnostic_language():
    biomarkers = [
        {"key": "serum_creatinine", "name": "Serum Creatinine", "value": 3.0, "unit": "mg/dL", "status": "High", "reference_range": "0.7 - 1.3"},
        {"key": "alt_sgpt", "name": "ALT (SGPT)", "value": 150.0, "unit": "U/L", "status": "High", "reference_range": "10 - 40"},
    ]
    res = generate_medical_explanation(report_type="LAB", biomarkers=biomarkers)

    full_text = str(res).lower()
    # Check that forbidden diagnostic terms and prescriptive language are absent
    assert "you have kidney disease" not in full_text
    assert "you have liver failure" not in full_text
    assert "you are diagnosed with" not in full_text
    assert "take medication" not in full_text
    assert "take 500mg" not in full_text
    assert "prescription" not in full_text
    assert res["disclaimer"] == DISCLAIMER_TEXT
