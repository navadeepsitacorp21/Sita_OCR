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
    assert bm_map["wbc_count"]["display_value"] == 6900.0
    assert bm_map["wbc_count"]["canonical_value"] == 6.9
    assert bm_map["wbc_count"]["canonical_unit"] == "10^3/uL"
    assert bm_map["wbc_count"]["status"] == "Normal"

    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["canonical_value"] == 221.0
    assert bm_map["platelet_count"]["canonical_unit"] == "10^3/uL"
    assert bm_map["platelet_count"]["status"] == "Normal"


def test_cbc_parser_with_ocr_confidence_scores():
    lines = [
        {"text": "HAEMOGLOBIN: 10.2 g/dL (12.5 - 16.0)", "confidence": 0.995},
        {"text": "Total Leucocyte Count (TLC): 12500 cells/cumm (4000-11000)", "confidence": 0.982}
    ]
    ocr_text = "\n".join([item["text"] for item in lines])
    result = parse_cbc_report(ocr_text, ocr_lines=lines)

    assert result["report_type"] == "CBC"
    assert result["biomarkers_found"] == 2
    assert result["status_summary"]["low"] == 1
    assert result["status_summary"]["high"] == 1

    bm_map = {b["key"]: b for b in result["biomarkers"]}

    assert bm_map["hemoglobin"]["value"] == 10.2
    assert bm_map["hemoglobin"]["status"] == "Low"
    assert bm_map["hemoglobin"]["ocr_confidence"] == 0.995

    assert bm_map["wbc_count"]["display_value"] == 12500.0
    assert bm_map["wbc_count"]["canonical_value"] == 12.5
    assert bm_map["wbc_count"]["canonical_unit"] == "10^3/uL"
    assert bm_map["wbc_count"]["status"] == "High"
    assert bm_map["wbc_count"]["ocr_confidence"] == 0.982


def test_cbc_parser_metadata_missing_keys():
    result = parse_cbc_report("General hospital visit summary without lab tests.")
    assert result["report_type"] == "CBC"
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

    # 1. Platelet Count (300000 /cumm, canonical 300 10^3/uL) -> Normal
    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["display_value"] == 300000.0
    assert bm_map["platelet_count"]["canonical_value"] == 300.0
    assert bm_map["platelet_count"]["canonical_unit"] == "10^3/uL"
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
    assert bm_map["wbc_count"]["display_value"] == 6200.0
    assert bm_map["wbc_count"]["canonical_value"] == 6.2
    assert bm_map["wbc_count"]["canonical_unit"] == "10^3/uL"
    assert bm_map["wbc_count"]["status"] == "Normal"
    assert bm_map["wbc_count"]["matched_alias"] == "tlc"

    # PLT -> platelet_count
    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["display_value"] == 250000.0
    assert bm_map["platelet_count"]["canonical_value"] == 250.0
    assert bm_map["platelet_count"]["canonical_unit"] == "10^3/uL"
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


EXACT_PROMPT_CBC_OCR_TEXT = """
PATIENT REPORT - COMPLETE BLOOD COUNT (CBC)

TEST NAME                   OBSERVED VALUE   UNIT          REFERENCE RANGE
Hemoglobin                  13.80            g/dL          12.0 - 15.0
RBC Count                   5.17             10^6/uL       4.0 - 5.2
Hematocrit                  41.50            %             36 - 46
MCV                         n0.30            fL            80 - 100
MCH                         26.70            pg            27 - 32
MCHC                        33.20            g/dL          31.5 - 34.5 RDW 12.20 % 11.5 - 14.5
WBC Count                   6.71             10^3/uL       4 - 10 10^3/uL
Platelet Count              265              10^3/uL       150 - 450
Neutrophils                 53.10            %             40 - 70
Lymphocytes                 35.00            %             20 - 40
Monocytes                   9.40             %             2 - 10
Eosinophils                 1.90             %             1 - 6
Basophils                   0.60             %             0 - 1
"""


def test_sita_v2_cbc_parser_all_bug_fixes():
    parsed = parse_cbc_report(EXACT_PROMPT_CBC_OCR_TEXT)
    assert parsed["report_type"] == "CBC"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 14

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # 1. Bug 1: MCV value parsing (n0.30 -> 80.30 fL, status = Normal)
    assert "mcv" in bm_map
    assert bm_map["mcv"]["value"] == 80.30
    assert bm_map["mcv"]["unit"] == "fL"
    assert bm_map["mcv"]["status"] == "Normal"
    assert "parser_confidence" in bm_map["mcv"]

    # 2. Bug 2: MCHC and RDW row isolation (MCHC=33.20 g/dL Normal, RDW=12.20 % Normal)
    assert "mchc" in bm_map
    assert bm_map["mchc"]["value"] == 33.20
    assert bm_map["mchc"]["status"] == "Normal"

    assert "rdw" in bm_map
    assert bm_map["rdw"]["value"] == 12.20
    assert bm_map["rdw"]["status"] == "Normal"

    # 3. Bug 3: WBC unit normalization (6.71 10^3/uL vs 4-10 -> Normal, not Low)
    assert "wbc_count" in bm_map
    assert bm_map["wbc_count"]["value"] == 6.71
    assert bm_map["wbc_count"]["status"] == "Normal"

    # 4. Bug 4: All 14 CBC biomarkers extracted
    expected_keys = [
        "hemoglobin", "rbc_count", "pcv", "mcv", "mch", "mchc", "rdw",
        "wbc_count", "platelet_count", "neutrophils", "lymphocytes",
        "monocytes", "eosinophils", "basophils"
    ]
    for key in expected_keys:
        assert key in bm_map, f"Missing required CBC biomarker: {key}"

    # Verify MCH is the only Low biomarker
    assert bm_map["mch"]["value"] == 26.70
    assert bm_map["mch"]["status"] == "Low"

    # Health summary counts
    assert parsed["status_summary"]["normal"] == 13
    assert parsed["status_summary"]["low"] == 1
    assert parsed["status_summary"]["high"] == 0


def test_labsmart_cbc_report_full():
    from app.services.health_summary_service import generate_health_summary

    labsmart_text = """
POWERED BY LABSMART SOFTWARE - COMPLETE BLOOD COUNT (CBC)

TEST NAME                   OBSERVED VALUE   UNIT          REFERENCE RANGE
Total Leukocyte Count       8,000            /cumm         4,000 - 11,000
Total RBC Count             5                10^6/uL       4.0 - 5.5
Hemoglobin                  13               g/dL          12.0 - 15.0
Platelets                   1,65,000         /cmm          1,60,000 - 4,50,000
Hematocrit                  47               %             40 - 50%
MCV                         94               fL            80 - 100
MCH                         26               pg            27 - 32
MCHC                        27.7             g/dL          31.5 - 34.5
Mean Platelet Volume        10               fL            7.5 - 11.5
RDW-CV                      10               %             11.5 - 14.5
RDW-SD                      40               fL            39 - 46
"""
    parsed = parse_cbc_report(labsmart_text)
    assert parsed["report_type"] == "CBC"
    assert parsed["hospital"] == "labsmart"
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 11

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # 1. WBC Count: display 8000 cells/cumm, canonical 8 10^3/uL, range 4-11, Normal
    assert bm_map["wbc_count"]["display_value"] == 8000.0
    assert bm_map["wbc_count"]["display_unit"] == "cells/cumm"
    assert bm_map["wbc_count"]["canonical_value"] == 8.0
    assert bm_map["wbc_count"]["canonical_unit"] == "10^3/uL"
    assert bm_map["wbc_count"]["status"] == "Normal"

    # 2. RBC Count: 5 10^6/uL, Normal
    assert bm_map["rbc_count"]["canonical_value"] == 5.0
    assert bm_map["rbc_count"]["canonical_unit"] == "10^6/uL"
    assert bm_map["rbc_count"]["status"] == "Normal"

    # 3. Hemoglobin: 13 g/dL, Normal
    assert bm_map["hemoglobin"]["canonical_value"] == 13.0
    assert bm_map["hemoglobin"]["canonical_unit"] == "g/dL"
    assert bm_map["hemoglobin"]["status"] == "Normal"

    # 4. Platelets: display 165000 /cmm, canonical 165 10^3/uL, range 160-450, Normal
    assert bm_map["platelet_count"]["display_value"] == 165000.0
    assert bm_map["platelet_count"]["display_unit"] == "cells/cumm"
    assert bm_map["platelet_count"]["canonical_value"] == 165.0
    assert bm_map["platelet_count"]["canonical_unit"] == "10^3/uL"
    assert bm_map["platelet_count"]["reference_range"] == "160 - 450"
    assert bm_map["platelet_count"]["status"] == "Normal"

    # 5. Hematocrit / PCV: 47% (40-50% OCR reference used over 36-46 fallback), Normal
    assert bm_map["pcv"]["canonical_value"] == 47.0
    assert bm_map["pcv"]["reference_range"] == "40 - 50"
    assert bm_map["pcv"]["reference_source"] == "report"
    assert bm_map["pcv"]["status"] == "Normal"

    # 6. MCV: 94 fL, Normal
    assert bm_map["mcv"]["canonical_value"] == 94.0
    assert bm_map["mcv"]["status"] == "Normal"

    # 7. MCH: 26 pg (27-32), Low
    assert bm_map["mch"]["canonical_value"] == 26.0
    assert bm_map["mch"]["status"] == "Low"

    # 8. MCHC: 27.7 g/dL (31.5-34.5), Low
    assert bm_map["mchc"]["canonical_value"] == 27.7
    assert bm_map["mchc"]["status"] == "Low"

    # 9. MPV: 10 fL (7.5-11.5), Normal
    assert bm_map["mpv"]["canonical_value"] == 10.0
    assert bm_map["mpv"]["status"] == "Normal"

    # 10. RDW-CV: 10% (11.5-14.5), Low
    assert bm_map["rdw_cv"]["canonical_value"] == 10.0
    assert bm_map["rdw_cv"]["status"] == "Low"

    # 11. RDW-SD: 40 fL (39-46), Normal
    assert bm_map["rdw_sd"]["canonical_value"] == 40.0
    assert bm_map["rdw_sd"]["status"] == "Normal"

    summary_res = generate_health_summary(parsed)
    summary = summary_res["summary"]
    assert summary["total"] == 11
    assert summary["normal"] == 8
    assert summary["low"] == 3
    assert summary["high"] == 0
    assert summary["needs_review"] == 0


def test_original_aster_cbc_screenshot():
    import os
    from app.services.ocr import get_ocr_provider
    from app.services.classifier_service import classify_report
    from app.services.report_router import route_report_parser

    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "ocr", "original_aster_cbc.png")
    if not os.path.exists(img_path):
        pytest.skip(f"Test image not found at {img_path}")

    ocr = get_ocr_provider()
    lines = ocr.extract_from_image(img_path)
    assert len(lines) > 0

    ocr_text = "\n".join([l["text"] for l in lines])
    clf = classify_report(ocr_text)
    assert clf["report_type"] == "CBC"

    parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["report_type"] == "CBC"
    assert parsed["parser_version"] == "1.3.2"
    assert parsed["biomarkers_found"] == 15
    assert len(parsed["biomarkers_missing"]) == 0

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # Verify all 15 parameters
    assert bm_map["rbc_count"]["value"] == 5.17
    assert bm_map["hemoglobin"]["value"] == 13.80
    assert bm_map["pcv"]["value"] == 41.50
    assert bm_map["mcv"]["value"] == 80.30
    assert bm_map["mch"]["value"] == 26.70
    assert bm_map["mchc"]["value"] == 33.30
    assert bm_map["rdw"]["value"] == 12.20
    assert bm_map["wbc_count"]["value"] == 6.71
    assert bm_map["neutrophils"]["value"] == 53.10
    assert bm_map["lymphocytes"]["value"] == 35.00
    assert bm_map["eosinophils"]["value"] == 1.90
    assert bm_map["monocytes"]["value"] == 9.40
    assert bm_map["basophils"]["value"] == 0.60
    assert bm_map["platelet_count"]["value"] == 265.00
    assert bm_map["mpv"]["value"] == 10.10

    # Status verifications
    assert bm_map["wbc_count"]["status"] == "Normal"
    assert bm_map["wbc_count"]["status"] != "Low"
    assert bm_map["platelet_count"]["status"] == "Normal"
    assert bm_map["mch"]["status"] == "Low"
    assert bm_map["mcv"]["status"] == "Low"
    assert bm_map["neutrophils"]["status"] == "Normal"
    assert bm_map["lymphocytes"]["status"] == "Normal"
    assert bm_map["eosinophils"]["status"] == "Normal"
    assert bm_map["monocytes"]["status"] == "Normal"
    assert bm_map["basophils"]["status"] == "Normal"


def test_cbc_negative_reference_safety():
    from app.services.report_router import route_report_parser

    # Negative test 1: WBC result = 6.71, reference = 4 - 10
    text_wbc = """
    COMPLETE BLOOD COUNT
    Total WBC Count    6.71    4 - 10    10^3/uL
    """
    res1 = route_report_parser("CBC", text_wbc)
    wbc = next(b for b in res1["biomarkers"] if b["key"] == "wbc_count")
    assert wbc["value"] == 6.71
    assert wbc["value"] != 4.0
    assert wbc["value"] != 10.0
    assert wbc["status"] == "Normal"

    # Negative test 2: Platelets result = 265, reference = 150 - 410
    text_plt = """
    COMPLETE BLOOD COUNT
    Platelet Count     265     150 - 410    10^3/uL
    """
    res2 = route_report_parser("CBC", text_plt)
    plt = next(b for b in res2["biomarkers"] if b["key"] == "platelet_count")
    assert plt["value"] == 265.0
    assert plt["value"] != 150.0
    assert plt["value"] != 410.0
    assert plt["status"] == "Normal"


def test_labsmart_cbc_11_parameters_extraction():
    import os
    from app.services.ocr import get_ocr_provider
    from app.services.classifier_service import classify_report
    from app.services.report_router import route_report_parser
    from app.api.medical_reports import _enrich_biomarkers, generate_deterministic_report_summary

    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "ocr", "labsmart_cbc_114550.png")
    if not os.path.exists(img_path):
        pytest.skip(f"Test image not found at {img_path}")

    ocr = get_ocr_provider()
    lines = ocr.extract_from_image(img_path)
    assert len(lines) > 0

    ocr_text = "\n".join([l["text"] for l in lines])
    clf = classify_report(ocr_text)
    assert clf["report_type"] == "CBC"

    parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["report_type"] == "CBC"
    raw_bms = parsed.get("biomarkers", [])
    assert len(raw_bms) == 11

    bm_map = {b["key"]: b for b in raw_bms}

    # Verify all 11 biomarkers exist with expected extracted values and units
    assert bm_map["mpv"]["value"] == 11.0
    assert bm_map["rdw_cv"]["value"] == 10.0
    assert bm_map["rdw_sd"]["value"] == 40.0
    assert bm_map["hemoglobin"]["value"] == 13.0
    assert bm_map["wbc_count"]["value"] == 8.0
    assert bm_map["rbc_count"]["value"] == 5.0
    assert bm_map["pcv"]["value"] == 47.0
    assert bm_map["mcv"]["value"] == 94.0
    assert bm_map["mch"]["value"] == 26.0
    assert bm_map["mchc"]["value"] == 27.7
    assert bm_map["platelet_count"]["value"] == 165.0

    # Enrich and verify deterministic status rule engine
    enriched = _enrich_biomarkers(raw_bms, "male")
    enriched_map = {b["key"]: b for b in enriched}

    # 3 Low abnormal parameters
    assert enriched_map["rdw_cv"]["status"] == "Low"
    assert enriched_map["mch"]["status"] == "Low"
    assert enriched_map["mchc"]["status"] == "Low"

    # 8 Normal parameters
    assert enriched_map["mpv"]["status"] == "Normal"
    assert enriched_map["rdw_sd"]["status"] == "Normal"
    assert enriched_map["hemoglobin"]["status"] == "Normal"
    assert enriched_map["wbc_count"]["status"] == "Normal"
    assert enriched_map["rbc_count"]["status"] == "Normal"
    assert enriched_map["pcv"]["status"] == "Normal"
    assert enriched_map["mcv"]["status"] == "Normal"
    assert enriched_map["platelet_count"]["status"] == "Normal"

    # Summary verification: 11 total, 8 normal, 3 below range, 0 above range
    summary = generate_deterministic_report_summary({"report_type": "CBC", "biomarkers": enriched}, patterns=[])
    assert summary["total_parameters"] == 11
    assert summary["normal"] == 8
    assert summary["abnormal_total"] == 3
    assert summary["low"] == 3
    assert summary["high"] == 0




