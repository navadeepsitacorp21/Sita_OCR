import os
import pytest
from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "ocr")


@pytest.fixture(scope="module")
def ocr_provider():
    return get_ocr_provider()


def test_ocr_golden_dataset_aster_cbc(ocr_provider):
    image_path = os.path.join(FIXTURES_DIR, "aster_cbc.png")
    assert os.path.exists(image_path), f"Fixture missing: {image_path}"

    lines = ocr_provider.extract_from_image(image_path)
    assert len(lines) > 0, "RapidOCR extracted no lines"

    # Verify bounding boxes and confidence structure
    for line in lines:
        assert "text" in line
        assert "confidence" in line
        assert "bbox" in line
        assert isinstance(line["confidence"], float)

    ocr_text = "\n".join([l["text"] for l in lines])
    classification = classify_report(ocr_text)
    assert classification["report_type"] == "CBC"

    parsed = route_report_parser(classification["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] >= 7

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert "hemoglobin" in bm_map
    assert bm_map["hemoglobin"]["value"] == 13.0
    assert "rbc_count" in bm_map
    assert bm_map["rbc_count"]["value"] == 4.8
    assert "wbc_count" in bm_map
    assert "pcv" in bm_map
    assert "mcv" in bm_map
    assert "mch" in bm_map
    assert "mchc" in bm_map


def test_ocr_golden_dataset_labsmart_cbc(ocr_provider):
    image_path = os.path.join(FIXTURES_DIR, "labsmart_cbc.png")
    assert os.path.exists(image_path), f"Fixture missing: {image_path}"

    lines = ocr_provider.extract_from_image(image_path)
    assert len(lines) > 0

    ocr_text = "\n".join([l["text"] for l in lines])
    classification = classify_report(ocr_text)
    assert classification["report_type"] == "CBC"

    parsed = route_report_parser(classification["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # Labsmart CBC expected values
    assert "wbc_count" in bm_map
    assert bm_map["wbc_count"]["canonical_value"] == 8.0
    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["canonical_value"] == 165.0
    assert "mcv" in bm_map
    assert bm_map["mcv"]["canonical_value"] == 94.0
    assert "mch" in bm_map
    assert bm_map["mch"]["canonical_value"] == 26.0
    assert "mpv" in bm_map
    assert bm_map["mpv"]["canonical_value"] == 10.0


def test_ocr_golden_dataset_care_diagnostics_lft(ocr_provider):
    image_path = os.path.join(FIXTURES_DIR, "lft_complete.png")
    assert os.path.exists(image_path), f"Fixture missing: {image_path}"

    lines = ocr_provider.extract_from_image(image_path)
    assert len(lines) > 0

    ocr_text = "\n".join([l["text"] for l in lines])
    classification = classify_report(ocr_text)
    assert classification["report_type"] == "LIVER_FUNCTION_TEST"

    parsed = route_report_parser(classification["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["parse_status"] == "success"
    assert parsed["biomarkers_found"] == 12
    assert len(parsed["biomarkers_missing"]) == 0

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # All 12 Biomarkers Validation with exact observed values and units
    assert "total_bilirubin" in bm_map
    assert bm_map["total_bilirubin"]["value"] == 0.8
    assert bm_map["total_bilirubin"]["unit"] == "mg/dL"
    assert bm_map["total_bilirubin"]["status"] == "Normal"

    assert "direct_bilirubin" in bm_map
    assert bm_map["direct_bilirubin"]["value"] == 0.2
    assert bm_map["direct_bilirubin"]["unit"] == "mg/dL"
    assert bm_map["direct_bilirubin"]["status"] == "Normal"

    assert "indirect_bilirubin" in bm_map
    assert bm_map["indirect_bilirubin"]["value"] == 0.6
    assert bm_map["indirect_bilirubin"]["unit"] == "mg/dL"
    assert bm_map["indirect_bilirubin"]["status"] == "Normal"

    assert "alt_sgpt" in bm_map
    assert bm_map["alt_sgpt"]["value"] == 32.0
    assert bm_map["alt_sgpt"]["value"] != 35.0
    assert bm_map["alt_sgpt"]["value"] != 45.0
    assert bm_map["alt_sgpt"]["unit"] == "U/L"
    assert bm_map["alt_sgpt"]["status"] == "Normal"

    assert "ast_sgot" in bm_map
    assert bm_map["ast_sgot"]["value"] == 29.0
    assert bm_map["ast_sgot"]["value"] != 35.0
    assert bm_map["ast_sgot"]["value"] != 40.0
    assert bm_map["ast_sgot"]["unit"] == "U/L"
    assert bm_map["ast_sgot"]["status"] == "Normal"

    assert "alkaline_phosphatase" in bm_map
    assert bm_map["alkaline_phosphatase"]["value"] == 94.0
    assert bm_map["alkaline_phosphatase"]["value"] != 44.0
    assert bm_map["alkaline_phosphatase"]["value"] != 147.0
    assert bm_map["alkaline_phosphatase"]["unit"] == "U/L"
    assert bm_map["alkaline_phosphatase"]["status"] == "Normal"

    assert "ggt" in bm_map
    assert bm_map["ggt"]["value"] == 28.0
    assert bm_map["ggt"]["value"] != 38.0
    assert bm_map["ggt"]["value"] != 55.0
    assert bm_map["ggt"]["unit"] == "U/L"
    assert bm_map["ggt"]["status"] == "Normal"

    assert "total_protein" in bm_map
    assert bm_map["total_protein"]["value"] == 7.2
    assert bm_map["total_protein"]["value"] != 6.0
    assert bm_map["total_protein"]["value"] != 8.3
    assert bm_map["total_protein"]["unit"] == "g/dL"
    assert bm_map["total_protein"]["status"] == "Normal"

    assert "albumin" in bm_map
    assert bm_map["albumin"]["value"] == 4.5
    assert bm_map["albumin"]["value"] != 3.5
    assert bm_map["albumin"]["value"] != 5.0
    assert bm_map["albumin"]["unit"] == "g/dL"
    assert bm_map["albumin"]["status"] == "Normal"

    assert "globulin" in bm_map
    assert bm_map["globulin"]["value"] == 2.7
    assert bm_map["globulin"]["value"] != 2.0
    assert bm_map["globulin"]["value"] != 3.5
    assert bm_map["globulin"]["unit"] == "g/dL"
    assert bm_map["globulin"]["status"] == "Normal"

    assert "albumin_globulin_ratio" in bm_map
    assert bm_map["albumin_globulin_ratio"]["value"] == 1.67
    assert bm_map["albumin_globulin_ratio"]["value"] != 1.0
    assert bm_map["albumin_globulin_ratio"]["value"] != 2.1
    assert bm_map["albumin_globulin_ratio"]["unit"] == "ratio"
    assert bm_map["albumin_globulin_ratio"]["status"] == "Normal"

    assert "ldh" in bm_map
    assert bm_map["ldh"]["value"] == 210.0
    assert bm_map["ldh"]["value"] != 140.0
    assert bm_map["ldh"]["value"] != 280.0
    assert bm_map["ldh"]["unit"] == "U/L"
    assert bm_map["ldh"]["status"] == "Normal"

    # Health summary verification
    summary = generate_health_summary(parsed)
    assert summary["overall_status"] == "Healthy"
    assert summary["abnormal_count"] == 0
    assert summary["normal_biomarkers"] == 12


def test_original_care_diagnostics_lft_screenshot(ocr_provider):
    """
    SITA OCR Engine v1.3.3 Original Image Fidelity & End-to-End Validation.
    Executes the exact real-world Care Diagnostics LFT screenshot through the
    full RapidOCR production pipeline, verifying:
    - 12/12 biomarker names resolved
    - Patient values correctly extracted without hallucination or reference confusion
    - Reference limits (e.g. ALT <45, GGT <55) NEVER returned as patient observations
    - Health summary calculated correctly
    """
    image_path = os.path.join(FIXTURES_DIR, "original_care_diagnostics_lft.png")
    assert os.path.exists(image_path), f"Original screenshot fixture missing: {image_path}"

    lines = ocr_provider.extract_from_image(image_path)
    assert len(lines) > 0, "RapidOCR extracted no lines from original screenshot"

    ocr_text = "\n".join([l["text"] for l in lines])
    classification = classify_report(ocr_text)
    assert classification["report_type"] == "LIVER_FUNCTION_TEST"

    parsed = route_report_parser(classification["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # 1. Total Bilirubin
    assert "total_bilirubin" in bm_map
    assert bm_map["total_bilirubin"]["value"] == 0.8
    assert bm_map["total_bilirubin"]["unit"] == "mg/dL"
    assert bm_map["total_bilirubin"]["status"] == "Normal"

    # 2. Direct Bilirubin
    assert "direct_bilirubin" in bm_map
    assert bm_map["direct_bilirubin"]["value"] == 0.2
    assert bm_map["direct_bilirubin"]["unit"] == "mg/dL"
    assert bm_map["direct_bilirubin"]["status"] == "Normal"

    # 3. Indirect Bilirubin
    assert "indirect_bilirubin" in bm_map
    assert bm_map["indirect_bilirubin"]["value"] == 0.6
    assert bm_map["indirect_bilirubin"]["unit"] == "mg/dL"
    assert bm_map["indirect_bilirubin"]["status"] == "Normal"

    # 4. ALT / SGPT (Patient = 32, Reference = Male <45, Female <35)
    assert "alt_sgpt" in bm_map
    assert bm_map["alt_sgpt"]["value"] == 32.0
    assert bm_map["alt_sgpt"]["value"] != 35.0, "Reference boundary Female 35 must not be result"
    assert bm_map["alt_sgpt"]["value"] != 45.0, "Reference boundary Male 45 must not be result"
    assert bm_map["alt_sgpt"]["unit"] == "U/L"
    assert bm_map["alt_sgpt"]["status"] == "Normal"

    # 5. AST / SGOT (Patient = 29, Reference = Male <40, Female <35)
    assert "ast_sgot" in bm_map
    assert bm_map["ast_sgot"]["value"] == 29.0
    assert bm_map["ast_sgot"]["value"] != 35.0, "Reference boundary Female 35 must not be result"
    assert bm_map["ast_sgot"]["value"] != 40.0, "Reference boundary Male 40 must not be result"
    assert bm_map["ast_sgot"]["unit"] == "U/L"
    assert bm_map["ast_sgot"]["status"] == "Normal"

    # 6. Alkaline Phosphatase (ALP) (Patient = 94, Reference = 40 - 129)
    assert "alkaline_phosphatase" in bm_map
    assert bm_map["alkaline_phosphatase"]["value"] == 94.0
    assert bm_map["alkaline_phosphatase"]["value"] != 40.0
    assert bm_map["alkaline_phosphatase"]["value"] != 129.0
    assert bm_map["alkaline_phosphatase"]["unit"] == "U/L"
    assert bm_map["alkaline_phosphatase"]["status"] == "Normal"

    # 7. GGT (Patient = 28, Reference = Male <55, Female <38)
    assert "ggt" in bm_map
    assert bm_map["ggt"]["value"] == 28.0
    assert bm_map["ggt"]["value"] != 38.0, "Reference boundary Female 38 must not be result"
    assert bm_map["ggt"]["value"] != 55.0, "Reference boundary Male 55 must not be result"
    assert bm_map["ggt"]["value"] != 7.2, "Subsequent biomarker value must not be stolen by GGT"
    assert bm_map["ggt"]["unit"] == "U/L"
    assert bm_map["ggt"]["status"] == "Normal"

    # 8. Total Protein (Patient = 7.2, Reference = 6.0 - 8.3)
    assert "total_protein" in bm_map
    assert bm_map["total_protein"]["value"] == 7.2
    assert bm_map["total_protein"]["value"] != 6.0
    assert bm_map["total_protein"]["value"] != 8.3
    assert bm_map["total_protein"]["unit"] == "g/dL"
    assert bm_map["total_protein"]["status"] == "Normal"

    # 9. Albumin (Patient = 4.5, Reference = 3.5 - 5.0)
    assert "albumin" in bm_map
    assert bm_map["albumin"]["value"] == 4.5
    assert bm_map["albumin"]["value"] != 3.5
    assert bm_map["albumin"]["value"] != 5.0
    assert bm_map["albumin"]["unit"] == "g/dL"
    assert bm_map["albumin"]["status"] == "Normal"

    # 10. Globulin (Patient = 2.7, Reference = 2.3 - 3.5)
    assert "globulin" in bm_map
    assert bm_map["globulin"]["value"] == 2.7
    assert bm_map["globulin"]["value"] != 2.3
    assert bm_map["globulin"]["value"] != 3.5
    assert bm_map["globulin"]["unit"] == "g/dL"
    assert bm_map["globulin"]["status"] == "Normal"

    # 11. A/G Ratio (Patient = 1.67, Reference = 1.0 - 2.1)
    assert "albumin_globulin_ratio" in bm_map
    assert bm_map["albumin_globulin_ratio"]["value"] == 1.67
    assert bm_map["albumin_globulin_ratio"]["value"] != 1.0
    assert bm_map["albumin_globulin_ratio"]["value"] != 2.1
    assert bm_map["albumin_globulin_ratio"]["unit"] == "ratio"
    assert bm_map["albumin_globulin_ratio"]["status"] == "Normal"

    # 12. LDH (Patient = 210, Reference = 140 - 280)
    assert "ldh" in bm_map
    assert bm_map["ldh"]["value"] == 210.0
    assert bm_map["ldh"]["value"] != 140.0
    assert bm_map["ldh"]["value"] != 280.0
    assert bm_map["ldh"]["unit"] == "U/L"
    assert bm_map["ldh"]["status"] == "Normal"

    assert parsed["biomarkers_found"] == 12
    assert len(parsed["biomarkers_missing"]) == 0

    # Health summary verification
    summary = generate_health_summary(parsed)
    assert summary["overall_status"] == "Healthy"
    assert summary["abnormal_count"] == 0
    assert summary["normal_biomarkers"] == 12


def test_original_care_diagnostics_kft_screenshot(ocr_provider):
    """
    SITA OCR ENGINE - KFT PARSER v1.3.x
    Full real-image Kidney Function Test (KFT) end-to-end validation.
    Exercises real RapidOCR ONNX + real KFT parser + real health summary pipeline.
    """
    image_path = os.path.join(FIXTURES_DIR, "original_care_diagnostics_kft.png")
    assert os.path.exists(image_path), f"Fixture missing: {image_path}"

    lines = ocr_provider.extract_from_image(image_path)
    assert len(lines) > 0, "RapidOCR extracted no lines"

    ocr_text = "\n".join([l["text"] for l in lines])
    classification = classify_report(ocr_text)
    assert classification["report_type"] == "KIDNEY_FUNCTION_TEST"

    parsed = route_report_parser(classification["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["parse_status"] == "success"
    assert parsed["parser_version"] == "1.3.2"
    assert parsed["biomarkers_found"] == 12
    assert len(parsed["biomarkers_missing"]) == 0

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # 1. Serum Urea (28 mg/dL, ref 15-40)
    assert "serum_urea" in bm_map
    assert bm_map["serum_urea"]["value"] == 28.0
    assert bm_map["serum_urea"]["unit"] == "mg/dL"
    assert bm_map["serum_urea"]["status"] == "Normal"

    # 2. Blood Urea Nitrogen (BUN) (13 mg/dL, ref 7-20)
    assert "bun" in bm_map
    assert bm_map["bun"]["value"] == 13.0
    assert bm_map["bun"]["unit"] == "mg/dL"
    assert bm_map["bun"]["status"] == "Normal"

    # 3. Serum Creatinine (0.9 mg/dL, ref Male 0.7-1.3, Female 0.6-1.1)
    assert "serum_creatinine" in bm_map
    assert bm_map["serum_creatinine"]["value"] == 0.9
    assert bm_map["serum_creatinine"]["unit"] == "mg/dL"
    assert bm_map["serum_creatinine"]["status"] == "Normal"

    # 4. Estimated Glomerular Filtration Rate (eGFR) (102 mL/min/1.73m², ref >=90)
    assert "egfr" in bm_map
    assert bm_map["egfr"]["value"] == 102.0
    assert bm_map["egfr"]["status"] == "Normal"

    # 5. Serum Uric Acid (5.4 mg/dL, ref Male 3.5-7.2, Female 2.6-6.0)
    assert "uric_acid" in bm_map
    assert bm_map["uric_acid"]["value"] == 5.4
    assert bm_map["uric_acid"]["unit"] == "mg/dL"
    assert bm_map["uric_acid"]["status"] == "Normal"

    # 6. Serum Sodium (140 mmol/L, ref 135-145)
    assert "sodium" in bm_map
    assert bm_map["sodium"]["value"] == 140.0
    assert bm_map["sodium"]["unit"] == "mmol/L"
    assert bm_map["sodium"]["status"] == "Normal"

    # 7. Serum Potassium (4.3 mmol/L, ref 3.5-5.0)
    assert "potassium" in bm_map
    assert bm_map["potassium"]["value"] == 4.3
    assert bm_map["potassium"]["unit"] == "mmol/L"
    assert bm_map["potassium"]["status"] == "Normal"

    # 8. Serum Chloride (103 mmol/L, ref 98-107)
    assert "chloride" in bm_map
    assert bm_map["chloride"]["value"] == 103.0
    assert bm_map["chloride"]["unit"] == "mmol/L"
    assert bm_map["chloride"]["status"] == "Normal"

    # 9. Serum Bicarbonate (CO₂, Total) (25 mmol/L, ref 22-29)
    assert "bicarbonate" in bm_map
    assert bm_map["bicarbonate"]["value"] == 25.0
    assert bm_map["bicarbonate"]["unit"] == "mmol/L"
    assert bm_map["bicarbonate"]["status"] == "Normal"

    # 10. Serum Calcium (9.4 mg/dL, ref 8.5-10.5)
    assert "calcium" in bm_map
    assert bm_map["calcium"]["value"] == 9.4
    assert bm_map["calcium"]["value"] != 8.51, "Calcium must not be 8.51"
    assert bm_map["calcium"]["unit"] == "mg/dL"
    assert bm_map["calcium"]["status"] == "Normal"

    # 11. Serum Phosphorus (3.7 mg/dL, ref 2.5-4.5)
    assert "phosphorus" in bm_map
    assert bm_map["phosphorus"]["value"] == 3.7
    assert bm_map["phosphorus"]["value"] != 2.1, "Phosphorus must not borrow Magnesium result 2.1"
    assert bm_map["phosphorus"]["unit"] == "mg/dL"
    assert bm_map["phosphorus"]["status"] == "Normal"

    # 12. Serum Magnesium (2.1 mg/dL, ref 1.7-2.4)
    assert "magnesium" in bm_map
    assert bm_map["magnesium"]["value"] == 2.1
    assert bm_map["magnesium"]["value"] != 3.7
    assert bm_map["magnesium"]["unit"] == "mg/dL"
    assert bm_map["magnesium"]["status"] == "Normal"

    # Overall Health Summary calculated dynamically
    health_summary = generate_health_summary(parsed)
    assert health_summary["overall_status"] == "Healthy"
    assert health_summary["total_biomarkers"] == 12
    assert health_summary["normal_biomarkers"] == 12
    assert health_summary["high_biomarkers"] == 0
    assert health_summary["low_biomarkers"] == 0
    assert health_summary["abnormal_count"] == 0



