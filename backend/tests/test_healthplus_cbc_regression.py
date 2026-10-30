import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ocr import get_ocr_provider
from app.parsers.cbc_parser import CBCParser
from app.services.medical_rule_engine import detect_cross_biomarker_patterns
from app.services.medical_explanation_engine import generate_medical_explanation

FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures",
    "ocr",
    "healthplus_cbc.webp"
)


@pytest.fixture(scope="module")
def ocr_results():
    assert os.path.exists(FIXTURE_PATH), f"Fixture not found at {FIXTURE_PATH}"
    import cv2
    img = cv2.imread(FIXTURE_PATH)
    provider = get_ocr_provider()
    lines = provider.extract_from_image(img)
    text = "\n".join([l["text"] for l in lines])
    return {"lines": lines, "text": text}


def test_healthplus_cbc_parser_all_15_biomarkers(ocr_results):
    """
    Verify CBC parser deterministically extracts all 15 biomarkers with exact values,
    correct units, report-provided reference intervals, and demographic statuses.
    """
    lines = ocr_results["lines"]
    text = ocr_results["text"]
    parser = CBCParser()
    parsed = parser.parse(text, lines)

    biomarkers = parsed.get("biomarkers", [])
    assert len(biomarkers) == 15, f"Expected 15 biomarkers, got {len(biomarkers)}"

    bm_map = {b["key"]: b for b in biomarkers}

    # 1. Haemoglobin
    assert "hemoglobin" in bm_map
    assert bm_map["hemoglobin"]["value"] == 13.2
    assert bm_map["hemoglobin"]["unit"] == "g/dL"
    assert bm_map["hemoglobin"]["reference_range"] == "13.0 - 17.0"
    assert bm_map["hemoglobin"]["reference_source"] == "report"
    assert bm_map["hemoglobin"]["status"] == "Normal"

    # 2. Total RBC Count
    assert "rbc_count" in bm_map
    assert bm_map["rbc_count"]["value"] == 5.10
    assert bm_map["rbc_count"]["unit"] == "10^6/uL"
    assert bm_map["rbc_count"]["reference_range"] == "4.5 - 5.5"
    assert bm_map["rbc_count"]["reference_source"] == "report"
    assert bm_map["rbc_count"]["status"] == "Normal"

    # 3. Packed Cell Volume (PCV/HCT)
    assert "pcv" in bm_map
    assert bm_map["pcv"]["value"] == 42.0
    assert bm_map["pcv"]["unit"] == "%"
    assert bm_map["pcv"]["reference_range"] == "40 - 50"
    assert bm_map["pcv"]["reference_source"] == "report"
    assert bm_map["pcv"]["status"] == "Normal"

    # 4. MCV
    assert "mcv" in bm_map
    assert bm_map["mcv"]["value"] == 82.0
    assert bm_map["mcv"]["unit"] == "fL"
    assert bm_map["mcv"]["reference_range"] == "80 - 100"
    assert bm_map["mcv"]["reference_source"] == "report"
    assert bm_map["mcv"]["status"] == "Normal"

    # 5. MCH
    assert "mch" in bm_map
    assert bm_map["mch"]["value"] == 25.9
    assert bm_map["mch"]["unit"] == "pg"
    assert bm_map["mch"]["reference_range"] == "27 - 32"
    assert bm_map["mch"]["reference_source"] == "report"
    assert bm_map["mch"]["status"] == "Low"

    # 6. MCHC
    assert "mchc" in bm_map
    assert bm_map["mchc"]["value"] == 31.4
    assert bm_map["mchc"]["unit"] == "g/dL"
    assert bm_map["mchc"]["reference_range"] == "32 - 36"
    assert bm_map["mchc"]["reference_source"] == "report"
    assert bm_map["mchc"]["status"] == "Low"

    # 7. RDW-CV
    assert "rdw_cv" in bm_map
    assert bm_map["rdw_cv"]["value"] == 13.6
    assert bm_map["rdw_cv"]["unit"] == "%"
    assert bm_map["rdw_cv"]["reference_range"] == "11.5 - 14.5"
    assert bm_map["rdw_cv"]["reference_source"] == "report"
    assert bm_map["rdw_cv"]["status"] == "Normal"

    # 8. Total WBC Count
    assert "wbc_count" in bm_map
    assert bm_map["wbc_count"]["value"] == 6.9
    assert bm_map["wbc_count"]["display_value"] == 6900.0
    assert bm_map["wbc_count"]["reference_range"] == "4 - 11"
    assert bm_map["wbc_count"]["reference_source"] == "report"
    assert bm_map["wbc_count"]["status"] == "Normal"

    # 9. Neutrophils
    assert "neutrophils" in bm_map
    assert bm_map["neutrophils"]["value"] == 40.0
    assert bm_map["neutrophils"]["unit"] == "%"
    assert bm_map["neutrophils"]["reference_range"] == "40 - 70"
    assert bm_map["neutrophils"]["reference_source"] == "report"
    assert bm_map["neutrophils"]["status"] == "Normal"

    # 10. Lymphocytes
    assert "lymphocytes" in bm_map
    assert bm_map["lymphocytes"]["value"] == 20.0
    assert bm_map["lymphocytes"]["unit"] == "%"
    assert bm_map["lymphocytes"]["reference_range"] == "20 - 40"
    assert bm_map["lymphocytes"]["reference_source"] == "report"
    assert bm_map["lymphocytes"]["status"] == "Normal"

    # 11. Monocytes
    assert "monocytes" in bm_map
    assert bm_map["monocytes"]["value"] == 6.0
    assert bm_map["monocytes"]["unit"] == "%"
    assert bm_map["monocytes"]["reference_range"] == "2 - 8"
    assert bm_map["monocytes"]["reference_source"] == "report"
    assert bm_map["monocytes"]["status"] == "Normal"

    # 12. Eosinophils
    assert "eosinophils" in bm_map
    assert bm_map["eosinophils"]["value"] == 6.0
    assert bm_map["eosinophils"]["unit"] == "%"
    assert bm_map["eosinophils"]["reference_range"] == "1 - 6"
    assert bm_map["eosinophils"]["reference_source"] == "report"
    assert bm_map["eosinophils"]["status"] == "Normal"

    # 13. Basophils
    assert "basophils" in bm_map
    assert bm_map["basophils"]["value"] == 1.0
    assert bm_map["basophils"]["unit"] == "%"
    assert bm_map["basophils"]["reference_range"] == "0 - 1"
    assert bm_map["basophils"]["reference_source"] == "report"
    assert bm_map["basophils"]["status"] == "Normal"

    # 14. Platelet Count
    assert "platelet_count" in bm_map
    assert bm_map["platelet_count"]["display_value"] == 1.8
    assert bm_map["platelet_count"]["reference_range"] == "1.5 - 4.0"
    assert bm_map["platelet_count"]["reference_source"] == "report"
    assert bm_map["platelet_count"]["status"] == "Normal"

    # 15. MPV
    assert "mpv" in bm_map
    assert bm_map["mpv"]["value"] == 8.0
    assert bm_map["mpv"]["unit"] == "fL"
    assert bm_map["mpv"]["reference_range"] == "7.5 - 11.5"
    assert bm_map["mpv"]["reference_source"] == "report"
    assert bm_map["mpv"]["status"] == "Normal"

    # Metadata checks
    metadata = parsed.get("metadata", {})
    assert metadata["report"]["report_date"] == "01/06/2026"
    assert metadata["patient"]["gender"] == "female"
    assert metadata["patient"]["age"] == 28


def test_healthplus_cbc_rule_engine_and_patterns(ocr_results):
    """
    Verify rule engine correctly evaluates 15 biomarkers, producing 0 abnormal patterns
    (no false anemia pattern).
    """
    lines = ocr_results["lines"]
    text = ocr_results["text"]
    parser = CBCParser()
    parsed = parser.parse(text, lines)
    biomarkers = parsed.get("biomarkers", [])

    patterns = detect_cross_biomarker_patterns(biomarkers, report_type="CBC")
    assert len(patterns) == 0, f"Expected 0 patterns for mild isolated MCH/MCHC low, got {patterns}"


def test_healthplus_cbc_explanation_engine(ocr_results):
    """
    Verify zero-LLM natural-language explanation receives the corrected 15-biomarker dataset
    and correctly highlights MCH and MCHC without generating erroneous diagnoses.
    """
    lines = ocr_results["lines"]
    text = ocr_results["text"]
    parser = CBCParser()
    parsed = parser.parse(text, lines)
    biomarkers = parsed.get("biomarkers", [])

    explanation = generate_medical_explanation(
        report_type="CBC",
        biomarkers=biomarkers,
        patterns=[],
        report_date="01/06/2026",
        patient_gender="female"
    )

    assert "MCH" in explanation["overall_explanation"]
    assert "MCHC" in explanation["overall_explanation"]
    assert len(explanation["key_findings"]) == 2
    assert any("MCH" in kf for kf in explanation["key_findings"])
    assert any("MCHC" in kf for kf in explanation["key_findings"])
    assert len(explanation["biomarker_explanations"]) == 2


def test_healthplus_cbc_api_endpoint_complete_flow():
    """
    Verify the complete POST /api/v1/medical-reports/analyze endpoint with HealthPlus CBC report.
    """
    client = TestClient(app)
    with open(FIXTURE_PATH, "rb") as f:
        response = client.post(
            "/api/v1/medical-reports/analyze",
            files={"file": ("healthplus_cbc.webp", f, "image/webp")},
            data={"patient_gender": "female"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["report_type"] == "CBC"
    assert data["report_date"] == "01/06/2026"
    assert data["patient_gender"] == "female"

    summary = data["summary"]
    assert summary["total_parameters"] == 15
    assert summary["normal"] == 13
    assert summary["low"] == 2
    assert summary["high"] == 0
    assert summary["needs_review"] == 0
    assert summary["abnormal_total"] == 2

    biomarkers = data["biomarkers"]
    assert len(biomarkers) == 15

    # Check that explanation is present and populated
    assert "explanation" in data
    assert len(data["explanation"]["key_findings"]) == 2
