"""
test_universal_reference_resolution.py
======================================
Tests verifying the Universal Reference Resolution policy:
Priority 1: Report Reference
Priority 2: SITA Biomarker Reference DB (Fallback)
Priority 3: Unknown / Needs Review
"""
import pytest
from app.utils.reference_resolver import (
    resolve_reference,
    detect_reference_type,
    validate_report_reference,
    parse_report_reference,
    build_structured_reference,
)
from app.services.parser_service import (
    parse_cbc_report,
    parse_liver_function_test_report,
    parse_kidney_function_test_report,
)


def test_reference_type_detection():
    # Standard range
    rtype, low, high = detect_reference_type("83 - 101")
    assert rtype == "range"
    assert low == 83.0
    assert high == 101.0

    # Upper bound (< 200)
    rtype, low, high = detect_reference_type("< 200")
    assert rtype == "upper_bound"
    assert low is None
    assert high == 200.0

    # Lower bound (> 40)
    rtype, low, high = detect_reference_type("> 40")
    assert rtype == "lower_bound"
    assert low == 40.0
    assert high is None

    # Gender specific
    rtype, _, _ = detect_reference_type("M: 13-17 F: 12-15")
    assert rtype == "gender_specific"

    # Invalid / plain string
    rtype, _, _ = detect_reference_type("mg/dL")
    assert rtype == "unknown"


def test_validate_report_reference():
    # Valid ranges and bounds
    assert validate_report_reference("83 - 101") is True
    assert validate_report_reference("< 40") is True
    assert validate_report_reference(">= 60") is True

    # Standalone numbers must be rejected
    assert validate_report_reference("0.60") is False
    assert validate_report_reference("13.5") is False

    # Standalone units must be rejected
    assert validate_report_reference("mg/dL", known_unit="mg/dL") is False
    assert validate_report_reference("", known_unit="g/dL") is False
    assert validate_report_reference(None) is False


def test_resolve_reference_priority():
    # Case 1: Report reference present and valid -> wins over sita_fallback
    res1 = resolve_reference(
        report_candidate="83 - 101",
        sita_fallback="80 - 100",
        biomarker_key="mcv"
    )
    assert res1.reference_source == "report"
    assert res1.reference_range == "83 - 101"
    assert res1.reference_type == "range"

    # Case 2: Report reference candidate is invalid (single number) -> falls back to sita_fallback
    res2 = resolve_reference(
        report_candidate="0.60",
        sita_fallback="0.0 - 0.2",
        biomarker_key="direct_bilirubin"
    )
    assert res2.reference_source == "fallback"
    assert res2.reference_range == "0.0 - 0.2"

    # Case 3: No report reference provided -> falls back to sita_fallback
    res3 = resolve_reference(
        report_candidate=None,
        sita_fallback="13.0 - 17.0",
        biomarker_key="hemoglobin"
    )
    assert res3.reference_source == "fallback"
    assert res3.reference_range == "13.0 - 17.0"

    # Case 4: Neither report nor sita_fallback available -> unknown
    res4 = resolve_reference(
        report_candidate=None,
        sita_fallback="",
        biomarker_key="custom_biomarker"
    )
    assert res4.reference_source == "unknown"
    assert res4.reference_type == "unknown"
    assert res4.reference_range == ""


def test_build_structured_reference():
    res = resolve_reference(
        report_candidate="10 - 20",
        sita_fallback="5 - 15"
    )
    struct = build_structured_reference(res)
    assert struct["source"] == "report"
    assert struct["type"] == "range"
    assert struct["lower_limit"] == 10.0
    assert struct["upper_limit"] == 20.0


def test_cbc_uses_report_reference_over_template():
    # Report printed range (e.g. 83-101) must override hospital template / default fallback (80-100)
    text = "MCV 89.0 fL 83 - 101"
    parsed = parse_cbc_report(text)
    bm = next(b for b in parsed["biomarkers"] if b["key"] == "mcv")
    assert bm["reference_source"] == "report"
    assert "83" in bm["reference_range"] and "101" in bm["reference_range"]


def test_lft_uses_report_reference_and_fallback():
    # LFT with report reference
    report_text = "TOTAL BILIRUBIN 0.9 mg/dL 0.2 - 1.2"
    parsed = parse_liver_function_test_report(report_text)
    bm = next(b for b in parsed["biomarkers"] if b["key"] == "total_bilirubin")
    assert bm["reference_source"] == "report"
    assert "0.2" in bm["reference_range"] and "1.2" in bm["reference_range"]

    # LFT without report reference uses fallback
    fallback_text = "TOTAL BILIRUBIN 0.9 mg/dL"
    parsed_fb = parse_liver_function_test_report(fallback_text)
    bm_fb = next(b for b in parsed_fb["biomarkers"] if b["key"] == "total_bilirubin")
    assert bm_fb["reference_source"] == "fallback"
    assert bm_fb["reference_range"] != ""


def test_kft_uses_report_reference_and_fallback():
    # KFT with report reference
    report_text = "SERUM CREATININE 1.0 mg/dL 0.7 - 1.3"
    parsed = parse_kidney_function_test_report(report_text)
    bm = next(b for b in parsed["biomarkers"] if b["key"] == "serum_creatinine")
    assert bm["reference_source"] == "report"
    assert "0.7" in bm["reference_range"] and "1.3" in bm["reference_range"]

    # KFT without report reference uses fallback
    fallback_text = "SERUM CREATININE 1.0 mg/dL"
    parsed_fb = parse_kidney_function_test_report(fallback_text)
    bm_fb = next(b for b in parsed_fb["biomarkers"] if b["key"] == "serum_creatinine")
    assert bm_fb["reference_source"] == "fallback"
    assert bm_fb["reference_range"] != ""


def test_reconstruct_fused_references():
    # 1. Fused integer range 1540 -> 15 - 40
    res_urea = resolve_reference("1540", "15-40")
    assert res_urea.reference_source == "report"
    assert res_urea.reference_range == "15 - 40"
    assert res_urea.reference_type == "range"
    assert res_urea.low == 15.0 and res_urea.high == 40.0

    # 2. Fused decimal range 8.510.5 -> 8.5 - 10.5
    res_calc = resolve_reference("8.510.5", "8.5-10.5")
    assert res_calc.reference_source == "report"
    assert res_calc.reference_range == "8.5 - 10.5"
    assert res_calc.reference_type == "range"
    assert res_calc.low == 8.5 and res_calc.high == 10.5


def test_corrupted_inequality_normalization():
    # 3. Corrupted inequality: ?55 -> <55, *2 -> <2
    res_corrupted = resolve_reference("?55", "10-49")
    assert res_corrupted.reference_source == "report"
    assert res_corrupted.reference_range in ["<55", ">=55", ">= 55", "< 55"]

    res_corrupted_unicode = resolve_reference("\ufffd55", "10-49")
    assert res_corrupted_unicode.reference_source == "report"
    assert res_corrupted_unicode.reference_range in ["<55", "< 55"]
    assert res_corrupted_unicode.reference_type == "upper_bound"
    assert res_corrupted_unicode.high == 55.0

    res_star = resolve_reference("*2", "0-2")
    assert res_star.reference_source == "report"
    assert res_star.reference_range in ["<2", "< 2"]
    assert res_star.reference_type == "upper_bound"
    assert res_star.high == 2.0


def test_gender_specific_reference_reconstruction():
    # 4. Gender-specific reference with typos/corrupted chars
    text = "Mele: \ufffd55, Female: 38"
    res = resolve_reference(text, "10-49")
    assert res.reference_source == "report"
    assert res.reference_type == "gender_specific"
    assert "Male: <55" in res.reference_range
    assert "Female: <38" in res.reference_range

    struct = build_structured_reference(res)
    assert struct["male"]["max"] == 55.0
    assert struct["female"]["max"] == 38.0


def test_observed_value_and_unit_protection():
    # 5. Single observed values MUST NOT become reference
    for obs in ["28", "80.3", "26.7", "6.71", "0.6", "265", "0.8", "0.2", "94", "7.2", "4.5", "2.7", "1.67", "210"]:
        res = resolve_reference(obs, "10-40")
        assert res.reference_source == "fallback"
        assert res.reference_range == "10-40"

    # 6. Units MUST NOT become reference
    for unit in ["mg/dL", "g/dL", "U/L", "mmol/L", "fL", "pg", "%", "10^3/uL"]:
        assert validate_report_reference(unit, known_unit=unit) is False
        res = resolve_reference(unit, "10-40", known_unit=unit)
        assert res.reference_source == "fallback"


def test_invalid_arbitrary_numbers_rejected_without_pattern():
    # 7. Arbitrary numbers that don't match any plausible range or fused pattern are rejected
    assert validate_report_reference("99999") is False
    res = resolve_reference("99999", "10-20")
    assert res.reference_source == "fallback"

