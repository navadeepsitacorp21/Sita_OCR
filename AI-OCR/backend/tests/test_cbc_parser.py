import pytest
from app.services.parser_service import parse_cbc_report

SAMPLE_CBC_OCR_TEXT = """
PATIENT REPORT - COMPLETE BLOOD COUNT (CBC)

TEST NAME                   OBSERVED VALUE   UNIT          REFERENCE RANGE
Hemoglobin (Hb)             12.6             gm/dL         12.5 - 16.0
RBC Count                   4.5              10^6/μL       4.0 - 5.5
WBC Count                   6900             cells/cu.mm   4000 - 10500
Platelet Count              221              10^3/μL       150 - 450
Packed Cell Volume (PCV)    38.5             %             36 - 46
MCV                         85.4             fL            80 - 100
MCH                         28.0             pg            27 - 32
MCHC                        32.8             g/dL          31.5 - 34.5
RDW-CV                      13.2             %             11.5 - 14.5
Neutrophils                 62.0             %             40 - 70
Lymphocytes                 30.0             %             20 - 40
Monocytes                   5.0              %             2 - 8
Eosinophils                 2.5              %             1 - 6
Basophils                   0.5              %             0 - 1
"""

def test_cbc_parser_basic():
    result = parse_cbc_report(SAMPLE_CBC_OCR_TEXT)
    assert result["report_type"] == "CBC"
    assert result["parser_version"] == "1.1.0"
    assert result["parse_status"] == "success"
    assert result["biomarkers_found"] >= 10
    assert isinstance(result["status_summary"], dict)

    biomarkers = result["biomarkers"]
    bm_map = {b["key"]: b for b in biomarkers}

    assert "hemoglobin" in bm_map
    assert bm_map["hemoglobin"]["value"] == 12.6
    assert bm_map["hemoglobin"]["unit"] in ["gm/dL", "g/dL"]
    assert bm_map["hemoglobin"]["reference_range"] == "12.5 - 16.0"
    assert bm_map["hemoglobin"]["status"] == "Normal"
    assert bm_map["hemoglobin"]["lower_limit"] == 12.5
    assert bm_map["hemoglobin"]["upper_limit"] == 16.0
    assert "ocr_confidence" in bm_map["hemoglobin"]

    assert "wbc_count" in bm_map
    assert bm_map["wbc_count"]["value"] == 6900
    assert bm_map["wbc_count"]["status"] == "Normal"

    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["value"] == 221
    assert bm_map["platelet_count"]["status"] == "Normal"

def test_cbc_parser_with_ocr_confidence_scores():
    lines = [
        {"text": "HAEMOGLOBIN: 10.2 g/dL (12.5 - 16.0)", "confidence": 0.995},
        {"text": "Total Leucocyte Count (TLC): 12500 cells/cumm (4000-11000)", "confidence": 0.982}
    ]
    ocr_text = "\n".join([item["text"] for item in lines])
    result = parse_cbc_report(ocr_text, ocr_lines=lines)

    assert result["report_type"] == "CBC"
    assert result["parser_version"] == "1.1.0"
    assert result["biomarkers_found"] == 2
    assert result["status_summary"]["low"] == 1
    assert result["status_summary"]["high"] == 1

    bm_map = {b["key"]: b for b in result["biomarkers"]}

    assert bm_map["hemoglobin"]["value"] == 10.2
    assert bm_map["hemoglobin"]["status"] == "Low"
    assert bm_map["hemoglobin"]["ocr_confidence"] == 0.995

    assert bm_map["wbc_count"]["value"] == 12500
    assert bm_map["wbc_count"]["status"] == "High"
    assert bm_map["wbc_count"]["ocr_confidence"] == 0.982

def test_cbc_parser_metadata_missing_keys():
    result = parse_cbc_report("General hospital visit summary without lab tests.")
    assert result["report_type"] == "CBC"
    assert result["parser_version"] == "1.1.0"
    assert result["parse_status"] == "no_biomarkers_found"
    assert result["biomarkers_found"] == 0
    assert len(result["biomarkers_missing"]) > 0
    assert result["biomarkers"] == []


FLABS_CBC_OCR_TEXT = """
FLABS DIAGNOSTICS - COMPLETE BLOOD COUNT (CBC)

Investigation              Result     Unit           Reference Range
Hemoglobin (Hb)            13.2       g/dL           12.0 - 15.0
RBC Count                  4.6        10^6/μL        4.0 - 5.2
Total Leucocytes (WBC)     7800       /cumm          4000 - 10000
Packed Cell Volume (PCV)   39.0       %              36 - 46
MCV                        80.0       fL             81 - 101
MCH                        28.5       pg             27 - 32
MCHC                       35.5       g/dL           31.5 - 34.5
RDW                        13.0       %              11.5 - 14.5
Platelet Count             300000     /cumm          150000 - 410000
Neutrophils                60         %              40 - 70
Lymphocytes                31         %              20 - 40
Monocytes                  5          %              2 - 10
Eosinophils                3          %              1 - 6
Basophils                  1          %              0 - 1
"""


def test_flabs_cbc_report_normalization_and_accuracy():
    from app.services.health_summary_service import generate_health_summary
    from app.services.health_highlights_service import generate_health_highlights

    parsed = parse_cbc_report(FLABS_CBC_OCR_TEXT)
    assert parsed["report_type"] == "CBC"
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # 1. Platelet Count (Normalized to 300 10^3/μL from 300000 /cumm, range 150-410) -> Normal
    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["value"] == 300.0
    assert bm_map["platelet_count"]["original_value"] == 300000.0
    assert bm_map["platelet_count"]["conversion_applied"] is True
    assert bm_map["platelet_count"]["status"] == "Normal"

    # 2. Monocytes (Uses report reference 2-10 instead of fallback 2-8) -> Normal
    assert "monocytes" in bm_map
    assert bm_map["monocytes"]["value"] == 5.0
    assert bm_map["monocytes"]["reference_source"] == "report"
    assert bm_map["monocytes"]["status"] == "Normal"

    # 3. MCV (80.0 vs 81-101) -> Low
    assert "mcv" in bm_map
    assert bm_map["mcv"]["value"] == 80.0
    assert bm_map["mcv"]["status"] == "Low"

    # 4. MCHC (35.5 vs 31.5-34.5) -> High
    assert "mchc" in bm_map
    assert bm_map["mchc"]["value"] == 35.5
    assert bm_map["mchc"]["status"] == "High"

    # 5. Health Summary
    summary = generate_health_summary(parsed)
    assert summary["overall_status"] == "Needs Attention"
    assert summary["abnormal_count"] == 2
    assert summary["high_biomarkers"] == 1
    assert summary["low_biomarkers"] == 1

    # 6. Health Highlights (Length = 2, containing MCV and MCHC, no Platelet or Monocyte)
    highlights_res = generate_health_highlights(parsed)
    highlights = highlights_res["highlights"]
    assert len(highlights) == 2
    highlight_keys = [h["key"] for h in highlights]
    assert "mcv" in highlight_keys
    assert "mchc" in highlight_keys
    assert "platelet_count" not in highlight_keys
    assert "monocytes" not in highlight_keys


ALT_LAB_CBC_OCR_TEXT = """
APOLLO DIAGNOSTICS - HAEMATOLOGY REPORT
HGB 15.0 g/dL (13.0 - 17.0)
TLC 6200 /cumm (4000 - 11000)
PLT 250000 /cumm (150000 - 450000)
HCT 42.0 % (36.0 - 48.0)
PMN 58.0 % (40.0 - 70.0)
"""


def test_cbc_parser_alternate_lab_terminology():
    parsed = parse_cbc_report(ALT_LAB_CBC_OCR_TEXT)
    assert parsed["report_type"] == "CBC"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 5

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # HGB -> hemoglobin
    assert "hemoglobin" in bm_map
    assert bm_map["hemoglobin"]["value"] == 15.0
    assert bm_map["hemoglobin"]["status"] == "Normal"
    assert bm_map["hemoglobin"]["matched_alias"] == "hgb"
    assert bm_map["hemoglobin"]["alias_source"] == "resolver"

    # TLC -> wbc_count
    assert "wbc_count" in bm_map
    assert bm_map["wbc_count"]["value"] == 6200.0
    assert bm_map["wbc_count"]["status"] == "Normal"
    assert bm_map["wbc_count"]["matched_alias"] == "tlc"
    assert bm_map["wbc_count"]["alias_source"] == "resolver"

    # PLT -> platelet_count (normalized from 250000 /cumm to 250)
    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["value"] == 250.0
    assert bm_map["platelet_count"]["status"] == "Normal"
    assert bm_map["platelet_count"]["matched_alias"] == "plt"

    # HCT -> pcv
    assert "pcv" in bm_map
    assert bm_map["pcv"]["value"] == 42.0
    assert bm_map["pcv"]["status"] == "Normal"
    assert bm_map["pcv"]["matched_alias"] == "hct"

    # PMN -> neutrophils
    assert "neutrophils" in bm_map
    assert bm_map["neutrophils"]["value"] == 58.0
    assert bm_map["neutrophils"]["status"] == "Normal"
    assert bm_map["neutrophils"]["matched_alias"] == "pmn"

