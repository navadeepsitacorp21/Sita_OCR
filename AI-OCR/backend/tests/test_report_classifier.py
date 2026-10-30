import pytest
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser


def test_classify_cbc():
    text = "COMPLETE BLOOD COUNT (CBC)\nHemoglobin 13.5 g/dL\nWBC Count 7000 cells/cumm\nPlatelet Count 250"
    res = classify_report(text)
    assert res["report_type"] == "CBC"
    assert res["confidence"] >= 0.70
    assert "hemoglobin" in res["matched_keywords"]
    assert res["matched_keyword_count"] >= 2
    assert res["classifier_version"] == "1.0.0"


def test_classify_lipid_profile():
    text = "LIPID PROFILE\nTotal Cholesterol 190 mg/dL\nHDL Cholesterol 45 mg/dL\nTriglycerides 150 mg/dL\nLDL 110"
    res = classify_report(text)
    assert res["report_type"] == "LIPID_PROFILE"
    assert res["confidence"] >= 0.70
    assert "cholesterol" in res["matched_keywords"] or "total cholesterol" in res["matched_keywords"]


def test_classify_diabetes_profile():
    text = "DIABETIC ASSESSMENT\nHbA1c 6.5 %\nEstimated Average Glucose (eAG) 140 mg/dL\nFasting Blood Sugar 110"
    res = classify_report(text)
    assert res["report_type"] == "DIABETES_PROFILE"
    assert res["confidence"] >= 0.70


def test_classify_thyroid_profile():
    text = "THYROID FUNCTION TEST\nTSH 2.5 uIU/mL\nTotal T3 1.2 ng/mL\nTotal T4 8.0 ug/dL"
    res = classify_report(text)
    assert res["report_type"] == "THYROID_PROFILE"
    assert res["confidence"] >= 0.70


def test_classify_liver_function_test():
    text = "LIVER FUNCTION TEST (LFT)\nBilirubin Total 0.8 mg/dL\nSGOT / AST 25 U/L\nSGPT / ALT 30 U/L\nAlkaline Phosphatase 85"
    res = classify_report(text)
    assert res["report_type"] == "LIVER_FUNCTION_TEST"
    assert res["confidence"] >= 0.70


def test_classify_kidney_function_test():
    text = "RENAL FUNCTION TEST (KFT / RFT)\nSerum Creatinine 0.9 mg/dL\nBlood Urea 24 mg/dL\nUric Acid 5.2"
    res = classify_report(text)
    assert res["report_type"] == "KIDNEY_FUNCTION_TEST"
    assert res["confidence"] >= 0.70


def test_classify_vitamin_profile():
    text = "SPECIALIZED LAB REPORT\n25-Hydroxy Vitamin D 32.0 ng/mL\nVitamin B12 450 pg/mL"
    res = classify_report(text)
    assert res["report_type"] == "VITAMIN_PROFILE"
    assert res["confidence"] >= 0.70


def test_classify_unknown_document():
    text = "Invoice #98234 for Hotel Stay in Goa. Total Amount: $250. Thank you for your business."
    res = classify_report(text)
    assert res["report_type"] == "UNKNOWN"
    assert res["confidence"] == 0.0
    assert res["matched_keywords"] == []
    assert res["matched_keyword_count"] == 0


def test_confidence_scaling():
    # 2 matches
    res_2 = classify_report("Hemoglobin and WBC report")
    # 4 matches
    res_4 = classify_report("Hemoglobin, WBC, Platelets, and RBC count report")
    assert res_4["confidence"] >= res_2["confidence"]


def test_report_router_cbc():
    text = "Hemoglobin 13.0 g/dL (12.5-16.0)\nWBC 6000 (4000-11000)"
    parsed = route_report_parser("CBC", text)
    assert parsed["report_type"] == "CBC"
    assert "biomarkers" in parsed
    assert len(parsed["biomarkers"]) >= 1


def test_report_router_unsupported_and_unknown():
    unknown = route_report_parser("UNKNOWN", "Invoice content")
    assert unknown["report_type"] == "UNKNOWN"
    assert unknown["status"] == "unknown_report_type"
    assert "CBC" in unknown["supported_report_types"]
    assert "LIPID_PROFILE" in unknown["supported_report_types"]
    assert "DIABETES_PROFILE" in unknown["supported_report_types"]
    assert "THYROID_PROFILE" in unknown["supported_report_types"]
    assert "LIVER_FUNCTION_TEST" in unknown["supported_report_types"]
    assert "KIDNEY_FUNCTION_TEST" in unknown["supported_report_types"]
    assert "VITAMIN_PROFILE" in unknown["supported_report_types"]
