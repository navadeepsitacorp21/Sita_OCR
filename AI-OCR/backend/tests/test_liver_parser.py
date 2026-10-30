import pytest
from app.services.parser_service import parse_liver_function_test_report
from app.services.report_router import route_report_parser


SAMPLE_LFT_TEXT = """
LIVER FUNCTION TEST (LFT)
Investigation               Observed Value    Unit      Reference Interval
Total Bilirubin             1.8               mg/dL     0.2-1.2
Direct Bilirubin            0.5               mg/dL     0.0-0.3
Indirect Bilirubin          1.3               mg/dL     0.2-0.9
SGOT / AST                  65                U/L       8-40
SGPT / ALT                  78                U/L       7-56
Alkaline Phosphatase (ALP)  120               U/L       44-147
Total Protein               7.2               g/dL      6.0-8.3
Albumin                     3.0               g/dL      3.5-5.0
Globulin                    4.2               g/dL      2.0-3.5
Albumin / Globulin Ratio    0.7               ratio     1.0-2.2
"""

SAMPLE_NORMAL_LFT_TEXT = """
LIVER FUNCTION TEST
Total Bilirubin             0.8 mg/dL (0.2-1.2)
Direct Bilirubin            0.2 mg/dL (0.0-0.3)
Indirect Bilirubin          0.6 mg/dL (0.2-0.9)
AST (SGOT)                  25 U/L (8-40)
ALT (SGPT)                  30 U/L (7-56)
Alkaline Phosphatase        90 U/L (44-147)
Total Protein               7.0 g/dL (6.0-8.3)
Albumin                     4.2 g/dL (3.5-5.0)
Globulin                    2.8 g/dL (2.0-3.5)
A/G Ratio                   1.5 ratio (1.0-2.2)
"""


def test_parse_complete_lft_report():
    parsed = parse_liver_function_test_report(SAMPLE_LFT_TEXT)
    assert parsed["report_type"] == "LIVER_FUNCTION_TEST"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 10
    assert len(parsed["biomarkers_missing"]) == 0

    keys = [b["key"] for b in parsed["biomarkers"]]
    assert "alt_sgpt" in keys
    assert "ast_sgot" in keys
    assert "alkaline_phosphatase" in keys
    assert "total_bilirubin" in keys
    assert "direct_bilirubin" in keys
    assert "indirect_bilirubin" in keys
    assert "total_protein" in keys
    assert "albumin" in keys
    assert "globulin" in keys
    assert "albumin_globulin_ratio" in keys


def test_alt_extraction():
    text = "SGPT / ALT 78 U/L (7-56)"
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "alt_sgpt"
    assert bm["value"] == 78.0
    assert bm["unit"] == "U/L"
    assert bm["status"] == "High"


def test_ast_extraction():
    text = "SGOT (AST) 65 U/L (8-40)"
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "ast_sgot"
    assert bm["value"] == 65.0
    assert bm["unit"] == "U/L"
    assert bm["status"] == "High"


def test_alp_extraction():
    text = "Alkaline Phosphatase 120 U/L (44-147)"
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "alkaline_phosphatase"
    assert bm["value"] == 120.0
    assert bm["unit"] == "U/L"
    assert bm["status"] == "Normal"


def test_total_bilirubin_extraction():
    text = "Total Bilirubin 1.8 mg/dL (0.2-1.2)"
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "total_bilirubin"
    assert bm["value"] == 1.8
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "High"


def test_direct_bilirubin_extraction():
    text = "Direct Bilirubin 0.1 mg/dL (0.0-0.3)"
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "direct_bilirubin"
    assert bm["value"] == 0.1
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "Normal"


def test_albumin_extraction():
    text = "Serum Albumin 4.0 g/dL (3.5-5.0)"
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "albumin"
    assert bm["value"] == 4.0
    assert bm["unit"] == "g/dL"
    assert bm["status"] == "Normal"


def test_high_alt_classification():
    text = "ALT 125 U/L (7-56)"
    parsed = parse_liver_function_test_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "High"
    assert "above the upper" in bm["status_reason"]


def test_high_total_bilirubin_classification():
    text = "Bilirubin Total 2.5 mg/dL (0.2-1.2)"
    parsed = parse_liver_function_test_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "High"
    assert "above the upper" in bm["status_reason"]


def test_low_albumin_classification():
    text = "Albumin 2.8 g/dL (3.5-5.0)"
    parsed = parse_liver_function_test_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["status"] == "Low"
    assert "below the lower" in bm["status_reason"]


def test_fallback_reference_ranges():
    # Report text with no reference ranges provided
    no_range_text = """
    SGPT 78 U/L
    Total Bilirubin 1.8 mg/dL
    Albumin 3.0 g/dL
    """
    parsed = parse_liver_function_test_report(no_range_text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    assert bm_map["alt_sgpt"]["reference_range"] == "7-56"
    assert bm_map["alt_sgpt"]["status"] == "High"

    assert bm_map["total_bilirubin"]["reference_range"] == "0.2-1.2"
    assert bm_map["total_bilirubin"]["status"] == "High"

    assert bm_map["albumin"]["reference_range"] == "3.5-5.0"
    assert bm_map["albumin"]["status"] == "Low"


def test_categories_generation():
    parsed = parse_liver_function_test_report(SAMPLE_LFT_TEXT)
    cats = parsed["categories"]
    assert "liver_enzymes" in cats
    assert "bilirubin" in cats
    assert "proteins" in cats
    assert "ratios" in cats

    assert "alt_sgpt" in cats["liver_enzymes"]
    assert "ast_sgot" in cats["liver_enzymes"]
    assert "alkaline_phosphatase" in cats["liver_enzymes"]

    assert "total_bilirubin" in cats["bilirubin"]
    assert "direct_bilirubin" in cats["bilirubin"]
    assert "indirect_bilirubin" in cats["bilirubin"]

    assert "albumin" in cats["proteins"]
    assert "globulin" in cats["proteins"]
    assert "total_protein" in cats["proteins"]

    assert "albumin_globulin_ratio" in cats["ratios"]


def test_parser_confidence_calculation():
    parsed = parse_liver_function_test_report(SAMPLE_LFT_TEXT)
    conf = parsed["parser_confidence"]
    assert conf["coverage_percent"] == 100.0
    assert conf["matched_biomarkers"] == 10
    assert conf["expected_biomarkers"] == 10

    # Partial report (3 out of 10)
    partial_text = "SGPT 45 U/L\nTotal Bilirubin 0.8 mg/dL\nAlbumin 4.0 g/dL"
    partial_parsed = parse_liver_function_test_report(partial_text)
    p_conf = partial_parsed["parser_confidence"]
    assert p_conf["coverage_percent"] == 30.0
    assert p_conf["matched_biomarkers"] == 3
    assert p_conf["expected_biomarkers"] == 10


def test_router_dispatch_lft():
    parsed = route_report_parser("LIVER_FUNCTION_TEST", SAMPLE_NORMAL_LFT_TEXT)
    assert parsed["report_type"] == "LIVER_FUNCTION_TEST"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 10
    assert parsed["status_summary"]["normal"] == 10
    assert parsed["status_summary"]["high"] == 0
    assert parsed["status_summary"]["low"] == 0
