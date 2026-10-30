import os
import pytest
from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.utils.metadata_extractor import extract_metadata, extract_laboratory_dates


def test_smart_pathology_kft_regression():
    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "ocr", "smart_pathology_kft.webp")
    if not os.path.exists(img_path):
        pytest.skip(f"Smart Pathology KFT image fixture not found at {img_path}")

    ocr = get_ocr_provider()
    lines = ocr.extract_from_image(img_path)
    assert len(lines) > 0

    ocr_text = "\n".join([l["text"] for l in lines])

    # 1. Classification
    clf = classify_report(ocr_text)
    assert clf["report_type"] == "KIDNEY_FUNCTION_TEST"

    # 2. Metadata / Report Date extraction
    meta = extract_metadata(ocr_text)
    rep_dates = extract_laboratory_dates(ocr_text)
    assert rep_dates["collection_date"] == "02/12/2022"
    assert rep_dates["reported_date"] == "02/12/2022"
    assert rep_dates["report_date"] == "02/12/2022"
    assert meta["report"]["report_date"] == "02/12/2022"

    # 3. Route parser
    parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=lines)
    assert parsed["report_type"] == "KIDNEY_FUNCTION_TEST"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # Exactly 11 parameters extracted
    expected_keys = [
        "serum_urea",
        "serum_creatinine",
        "uric_acid",
        "calcium",
        "phosphorus",
        "alkaline_phosphatase",
        "total_protein",
        "albumin",
        "sodium",
        "potassium",
        "chloride"
    ]
    assert len(parsed["biomarkers"]) == 11
    for k in expected_keys:
        assert k in bm_map, f"Missing expected KFT biomarker: {k}"

    # Specifically verify previously missing parameters are fixed
    assert "alkaline_phosphatase" in bm_map
    assert bm_map["alkaline_phosphatase"]["value"] == 80.0
    assert bm_map["alkaline_phosphatase"]["unit"] == "U/L"
    assert bm_map["alkaline_phosphatase"]["reference_range"] == "30 - 120"
    assert bm_map["alkaline_phosphatase"]["reference_source"] == "report"
    assert bm_map["alkaline_phosphatase"]["status"] == "Normal"

    assert "total_protein" in bm_map
    assert bm_map["total_protein"]["value"] == 5.9
    assert bm_map["total_protein"]["unit"] == "g/dL"
    assert bm_map["total_protein"]["reference_range"] == "5.7 - 8.2"
    assert bm_map["total_protein"]["reference_source"] == "report"
    assert bm_map["total_protein"]["status"] == "Normal"

    assert "albumin" in bm_map
    assert bm_map["albumin"]["value"] == 4.1
    assert bm_map["albumin"]["unit"] == "g/dL"
    assert bm_map["albumin"]["reference_range"] == "3.2 - 4.8"
    assert bm_map["albumin"]["reference_source"] == "report"
    assert bm_map["albumin"]["status"] == "Normal"

    assert "sodium" in bm_map
    assert bm_map["sodium"]["value"] == 139.0
    assert bm_map["sodium"]["reference_range"] == "136 - 145"
    assert bm_map["sodium"]["reference_source"] == "report"
    assert bm_map["sodium"]["status"] == "Normal"

    assert "potassium" in bm_map
    assert bm_map["potassium"]["value"] == 3.9
    assert bm_map["potassium"]["reference_range"] == "3.5 - 5.1"
    assert bm_map["potassium"]["reference_source"] == "report"
    assert bm_map["potassium"]["status"] == "Normal"

    assert "chloride" in bm_map
    assert bm_map["chloride"]["value"] == 100.0
    assert bm_map["chloride"]["reference_range"] == "98 - 107"
    assert bm_map["chloride"]["reference_source"] == "report"
    assert bm_map["chloride"]["status"] == "Normal"

    # Report references are preserved (not generic SITA fallbacks)
    assert bm_map["serum_urea"]["value"] == 15.0
    assert bm_map["serum_urea"]["reference_range"] == "13 - 43"
    assert bm_map["serum_urea"]["reference_source"] == "report"
    assert bm_map["serum_urea"]["status"] == "Normal"

    assert bm_map["serum_creatinine"]["value"] == 1.5
    assert bm_map["serum_creatinine"]["reference_range"] == "0.7 - 1.3"
    assert bm_map["serum_creatinine"]["reference_source"] == "report"
    assert bm_map["serum_creatinine"]["status"] == "High"

    assert bm_map["uric_acid"]["value"] == 5.5
    assert bm_map["uric_acid"]["reference_range"] == "3.5 - 7.2"
    assert bm_map["uric_acid"]["reference_source"] == "report"
    assert bm_map["uric_acid"]["status"] == "Normal"

    assert bm_map["calcium"]["value"] == 10.2
    assert bm_map["calcium"]["reference_range"] == "8.7 - 10.4"
    assert bm_map["calcium"]["reference_source"] == "report"
    assert bm_map["calcium"]["status"] == "Normal"

    assert bm_map["phosphorus"]["value"] == 1.4
    assert bm_map["phosphorus"]["reference_range"] == "2.4 - 5.1"
    assert bm_map["phosphorus"]["reference_source"] == "report"
    assert bm_map["phosphorus"]["status"] == "Low"

    # Status summary: 9 Normal (Within Range), 2 Abnormal (Outside Range: High / Low)
    summary = parsed["status_summary"]
    assert summary["normal"] == 9
    assert summary["high"] == 1
    assert summary["low"] == 1

    # Verify unrelated report text was NOT extracted as biomarkers
    extracted_keys = set(bm_map.keys())
    assert "magnesium" not in extracted_keys
    assert "bun" not in extracted_keys
    assert "egfr" not in extracted_keys
    assert "bicarbonate" not in extracted_keys


def test_smart_pathology_kft_analyze_api_regression():
    from fastapi.testclient import TestClient
    from app.main import app
    from datetime import datetime

    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "ocr", "smart_pathology_kft.webp")
    if not os.path.exists(img_path):
        pytest.skip(f"Smart Pathology KFT image fixture not found at {img_path}")

    client = TestClient(app)
    with open(img_path, "rb") as f:
        response = client.post(
            "/api/v1/medical-reports/analyze",
            files={"file": ("smart_pathology_kft.webp", f, "image/webp")},
        )

    assert response.status_code == 200
    data = response.json()

    # 1. Smart Pathology KFT produces 11 biomarkers.
    biomarkers = data.get("biomarkers", [])
    assert len(biomarkers) == 11
    bm_map = {b["key"]: b for b in biomarkers}

    # 2. Albumin is present in the final analyze response.
    assert "albumin" in bm_map
    alb = bm_map["albumin"]
    assert alb["value"] == 4.1
    assert alb["unit"] == "g/dL"
    assert alb["reference_range"] == "3.2 - 4.8"

    # 3. Albumin status is normal.
    assert alb["status"].lower() in ["normal", "within range"]

    # 4. Total biomarker count = 11.
    summary = data.get("summary", {})
    assert summary.get("total_parameters") == 11

    # 5. Normal count = 9.
    assert summary.get("normal") == 9

    # 6. Low count = 1.
    assert summary.get("low") == 1

    # 7. High count = 1.
    assert summary.get("high") == 1

    # 8. Outside count = 2.
    assert summary.get("abnormal_total") == 2

    # 9. Report date = 02/12/2022.
    assert data.get("report_date") == "02/12/2022"
    assert data.get("collection_date") == "02/12/2022"
    assert data.get("reported_date") == "02/12/2022"

    # 10. Analyzed timestamp remains the current processing timestamp.
    analyzed_at = data.get("analyzed_at")
    assert analyzed_at is not None
    # Verify it is valid ISO timestamp and separate from report_date
    parsed_analyzed = datetime.fromisoformat(analyzed_at)
    assert parsed_analyzed is not None
    assert analyzed_at != data.get("report_date")

    # 11. Explanation still exists and is generated from the complete analysis.
    explanation = data.get("explanation")
    assert explanation is not None
    assert "overall_explanation" in explanation
    assert "Creatinine" in explanation["overall_explanation"]
    assert "Phosphorus" in explanation["overall_explanation"]

