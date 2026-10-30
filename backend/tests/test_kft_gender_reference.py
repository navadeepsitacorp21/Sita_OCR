import pytest
from app.services.status_engine import calculate_status, parse_reference_range_bounds
from app.utils.reference_resolver import resolve_reference, clean_ocr_reference_artifacts, reconstruct_fused_reference
from app.api.medical_reports import _enrich_biomarkers
from app.services.medical_rule_engine import generate_deterministic_report_summary, detect_cross_biomarker_patterns


def test_gender_specific_kft_reference_resolution_preserves_both_ranges():
    # 1. Creatinine with OCR typo 'Msle: 0.7-1.3, Female: 0.6-11'
    tok1 = "Msle: 0.7-1.3, Female: 0.6-11"
    cleaned1 = clean_ocr_reference_artifacts(tok1)
    reconstructed1 = reconstruct_fused_reference(cleaned1)
    res1 = resolve_reference(reconstructed1, "0.7-1.3")
    assert res1.reference_source == "report"
    assert res1.reference_type == "gender_specific"
    assert "Male: 0.7 - 1.3" in res1.reference_range
    assert "Female: 0.6 - 1.1" in res1.reference_range

    # 2. Uric acid with fused decimals 'Male: 3.57.2, Female: 2.6-6.0'
    tok2 = "Male: 3.57.2, Female: 2.6-6.0"
    cleaned2 = clean_ocr_reference_artifacts(tok2)
    reconstructed2 = reconstruct_fused_reference(cleaned2)
    res2 = resolve_reference(reconstructed2, "3.5-7.2")
    assert res2.reference_source == "report"
    assert res2.reference_type == "gender_specific"
    assert "Male: 3.5 - 7.2" in res2.reference_range
    assert "Female: 2.6 - 6.0" in res2.reference_range


def test_calculate_status_gender_specific_requires_gender():
    ref_creat = "Male: 0.7 - 1.3, Female: 0.6 - 1.1"
    ref_uric = "Male: 3.5 - 7.2, Female: 2.6 - 6.0"

    # Not specified / unknown / empty
    for g in ["unknown", "not_specified", "", "Not Specified", None]:
        res_c = calculate_status(0.9, ref_creat, gender=g or "unknown")
        assert res_c["status"] == "Needs Review"
        assert "gender" in res_c["status_reason"].lower()
        assert res_c["lower_limit"] is None
        assert res_c["upper_limit"] is None

        res_u = calculate_status(5.4, ref_uric, gender=g or "unknown")
        assert res_u["status"] == "Needs Review"
        assert "gender" in res_u["status_reason"].lower()

    # Male
    res_c_male = calculate_status(0.9, ref_creat, gender="male")
    assert res_c_male["status"] == "Normal"
    assert res_c_male["lower_limit"] == 0.7
    assert res_c_male["upper_limit"] == 1.3

    res_u_male = calculate_status(5.4, ref_uric, gender="male")
    assert res_u_male["status"] == "Normal"
    assert res_u_male["lower_limit"] == 3.5
    assert res_u_male["upper_limit"] == 7.2

    # Female
    res_c_fem = calculate_status(0.9, ref_creat, gender="female")
    assert res_c_fem["status"] == "Normal"
    assert res_c_fem["lower_limit"] == 0.6
    assert res_c_fem["upper_limit"] == 1.1

    res_u_fem = calculate_status(5.4, ref_uric, gender="female")
    assert res_u_fem["status"] == "Normal"
    assert res_u_fem["lower_limit"] == 2.6
    assert res_u_fem["upper_limit"] == 6.0


def test_gender_independent_kft_reference_evaluates_normally():
    ref_urea = "15 - 40"
    for g in ["unknown", "male", "female", ""]:
        res = calculate_status(28.0, ref_urea, gender=g or "unknown")
        assert res["status"] == "Normal"
        assert res["lower_limit"] == 15.0
        assert res["upper_limit"] == 40.0


def test_enrich_biomarkers_kft_gender_modes():
    raw_biomarkers = [
        {
            "key": "serum_creatinine",
            "name": "Serum Creatinine",
            "value": 0.9,
            "unit": "mg/dL",
            "reference_range": "Male: 0.7 - 1.3, Female: 0.6 - 1.1",
            "reference_source": "report",
            "structured_reference": {"type": "gender_specific"},
            "status": "Needs Review",
        },
        {
            "key": "uric_acid",
            "name": "Serum Uric Acid",
            "value": 5.4,
            "unit": "mg/dL",
            "reference_range": "Male: 3.5 - 7.2, Female: 2.6 - 6.0",
            "reference_source": "report",
            "structured_reference": {"type": "gender_specific"},
            "status": "Needs Review",
        },
        {
            "key": "serum_urea",
            "name": "Serum Urea",
            "value": 28.0,
            "unit": "mg/dL",
            "reference_range": "15 - 40",
            "reference_source": "report",
            "structured_reference": {"type": "range"},
            "status": "Normal",
        },
    ]

    # Mode 1: Not Specified (unknown)
    enriched_unspec = _enrich_biomarkers(raw_biomarkers, "unknown")
    bm_u = {b["key"]: b for b in enriched_unspec}
    assert bm_u["serum_creatinine"]["status"] == "Needs Review"
    assert bm_u["uric_acid"]["status"] == "Needs Review"
    assert bm_u["serum_urea"]["status"] == "Normal"
    # Preserves both gender ranges in the reference_range string
    assert "Male: 0.7 - 1.3" in bm_u["serum_creatinine"]["reference_range"]
    assert "Female: 0.6 - 1.1" in bm_u["serum_creatinine"]["reference_range"]

    # Verify summary contributions
    patterns = detect_cross_biomarker_patterns(enriched_unspec, report_type="KIDNEY_FUNCTION_TEST")
    summary = generate_deterministic_report_summary({"report_type": "KIDNEY_FUNCTION_TEST", "biomarkers": enriched_unspec}, patterns)
    assert summary["normal"] == 1
    assert summary["needs_review"] == 2
    assert summary["abnormal_total"] == 0

    # Mode 2: Male
    enriched_male = _enrich_biomarkers(raw_biomarkers, "male")
    bm_m = {b["key"]: b for b in enriched_male}
    assert bm_m["serum_creatinine"]["status"] == "Normal"
    assert bm_m["serum_creatinine"]["lower_limit"] == 0.7
    assert bm_m["serum_creatinine"]["upper_limit"] == 1.3
    assert bm_m["uric_acid"]["status"] == "Normal"
    assert bm_m["uric_acid"]["lower_limit"] == 3.5
    assert bm_m["uric_acid"]["upper_limit"] == 7.2

    # Mode 3: Female
    enriched_fem = _enrich_biomarkers(raw_biomarkers, "female")
    bm_f = {b["key"]: b for b in enriched_fem}
    assert bm_f["serum_creatinine"]["status"] == "Normal"
    assert bm_f["serum_creatinine"]["lower_limit"] == 0.6
    assert bm_f["serum_creatinine"]["upper_limit"] == 1.1
    assert bm_f["uric_acid"]["status"] == "Normal"
    assert bm_f["uric_acid"]["lower_limit"] == 2.6
    assert bm_f["uric_acid"]["upper_limit"] == 6.0
