import pytest
from app.services.medical_rule_engine import (
    interpret_biomarker,
    detect_cross_biomarker_patterns,
    generate_deterministic_report_summary
)


def test_dual_range_interpretation():
    # MCV low
    interp = interpret_biomarker("mcv", "Low", value=80.3, unit="fL", reference_range="83 - 101")
    assert "Microcytosis" in interp["title"] or "Low MCV" in interp["title"]
    assert "iron deficiency" in str(interp["possible_associations"]).lower()
    assert "educational" in interp["disclaimer"].lower()

    # Normal Hemoglobin
    interp_normal = interpret_biomarker("hemoglobin", "Normal", value=14.0, unit="g/dL", reference_range="13 - 17")
    assert interp_normal["title"] == "Normal Hemoglobin"


def test_upper_bound_interpretation():
    # ALT high
    interp = interpret_biomarker("alt_sgpt", "High", value=65.0, unit="U/L", reference_range="<45")
    assert "Elevated ALT" in interp["title"]
    assert any("liver" in a.lower() for a in interp["possible_associations"])


def test_lower_bound_interpretation():
    # eGFR low
    interp = interpret_biomarker("egfr", "Low", value=55.0, unit="mL/min/1.73m2", reference_range=">= 90")
    assert "Reduced eGFR" in interp["title"]


def test_gender_specific_needs_review():
    # When status is "Needs Review"
    interp = interpret_biomarker("ast_sgot", "Needs Review", value=38.0, unit="U/L", reference_range="Male: <=40, Female: <=35")
    assert "Needs Clinical Review" in interp["title"]


def test_cross_biomarker_patterns_cbc():
    biomarkers = [
        {"key": "mcv", "status": "Low", "value": 80.3},
        {"key": "mch", "status": "Low", "value": 26.7},
        {"key": "hemoglobin", "status": "Low", "value": 11.2},
    ]
    patterns = detect_cross_biomarker_patterns(biomarkers, report_type="CBC")
    pattern_ids = [p["pattern_id"] for p in patterns]
    assert "low_red_cell_indices" in pattern_ids
    assert "anemia_pattern" in pattern_ids


def test_cross_biomarker_patterns_lft():
    biomarkers = [
        {"key": "alt_sgpt", "status": "High", "value": 75.0},
        {"key": "ast_sgot", "status": "High", "value": 68.0},
    ]
    patterns = detect_cross_biomarker_patterns(biomarkers, report_type="LIVER_FUNCTION_TEST")
    assert len(patterns) == 1
    assert patterns[0]["pattern_id"] == "hepatocellular_transaminitis"


def test_cross_biomarker_patterns_kft():
    biomarkers = [
        {"key": "serum_creatinine", "status": "High", "value": 1.8},
        {"key": "serum_urea", "status": "High", "value": 65.0},
    ]
    patterns = detect_cross_biomarker_patterns(biomarkers, report_type="KIDNEY_FUNCTION_TEST")
    assert len(patterns) == 1
    assert patterns[0]["pattern_id"] == "azotemia_renal_pattern"


def test_deterministic_summary_generation():
    parsed = {
        "report_type": "CBC",
        "biomarkers": [
            {"key": "mcv", "status": "Low"},
            {"key": "mch", "status": "Low"},
            {"key": "rbc_count", "status": "Normal"},
            {"key": "hemoglobin", "status": "Normal"},
        ]
    }
    patterns = detect_cross_biomarker_patterns(parsed["biomarkers"], "CBC")
    summary = generate_deterministic_report_summary(parsed, patterns)

    assert summary["total_parameters"] == 4
    assert summary["normal"] == 2
    assert summary["low"] == 2
    assert summary["abnormal_total"] == 2
    assert "CBC contains 4 analyzed parameters" in summary["narrative"]
    assert "2 below range" in summary["narrative"]
