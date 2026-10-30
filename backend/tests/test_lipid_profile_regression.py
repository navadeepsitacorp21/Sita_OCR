import io
import pytest
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.parser_service import parse_lipid_profile_report
from app.database.database import SessionLocal
from app.database.models import HealthReport

client = TestClient(app)

SAMPLE_LIPID_REPORT_TEXT = """
METROPOLIS DIAGNOSTIC SERVICES
PATIENT LAB REPORT - LIPID PROFILE
Patient Name: John Doe    Age: 45 Y / Male
Date of Collection: 15 Oct 2026   Report Date: 16 Oct 2026

TEST NAME                     OBSERVED VALUE   UNIT          REFERENCE INTERVAL
Total Cholesterol             235.0            mg/dL         <200
Triglycerides                 185.0            mg/dL         <150
HDL Cholesterol               36.0             mg/dL         >40
LDL Cholesterol               155.0            mg/dL         <100
VLDL Cholesterol              37.0             mg/dL         5 - 40
Non-HDL Cholesterol           199.0            mg/dL         <130
TC/HDL Ratio                  6.5              ratio         3.0 - 5.0
LDL/HDL Ratio                 4.3              ratio         <3.0
Apolipoprotein A1 (ApoA1)     105.0            mg/dL         110 - 205
Apolipoprotein B (ApoB)       140.0            mg/dL         60 - 130
"""


def test_lipid_report_classification():
    """Test 1: Lipid Profile is correctly classified as LIPID_PROFILE."""
    classification = classify_report(SAMPLE_LIPID_REPORT_TEXT)
    assert classification["report_type"] == "LIPID_PROFILE"
    assert classification["confidence"] >= 0.70
    assert "lipid profile" in [k.lower() for k in classification["matched_keywords"]]


def test_lipid_report_routing_and_biomarker_extraction():
    """
    Test 2 & 3: Lipid Profile is routed to the Lipid parser and extracts
    all 10 expected lipid biomarkers.
    """
    parsed = route_report_parser("LIPID_PROFILE", SAMPLE_LIPID_REPORT_TEXT)
    assert parsed["report_type"] == "LIPID_PROFILE"
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # Core lipid biomarkers
    assert "total_cholesterol" in bm_map
    assert bm_map["total_cholesterol"]["value"] == 235.0
    assert bm_map["total_cholesterol"]["status"] == "High"
    assert bm_map["total_cholesterol"]["reference_range"] == "<200"

    assert "triglycerides" in bm_map
    assert bm_map["triglycerides"]["value"] == 185.0
    assert bm_map["triglycerides"]["status"] == "High"

    assert "hdl" in bm_map
    assert bm_map["hdl"]["value"] == 36.0
    assert bm_map["hdl"]["status"] == "Low"

    assert "ldl" in bm_map
    assert bm_map["ldl"]["value"] == 155.0
    assert bm_map["ldl"]["status"] == "High"

    assert "vldl" in bm_map
    assert bm_map["vldl"]["value"] == 37.0
    assert bm_map["vldl"]["status"] == "Normal"

    assert "non_hdl" in bm_map
    assert bm_map["non_hdl"]["value"] == 199.0
    assert bm_map["non_hdl"]["status"] == "High"

    assert "cholesterol_hdl_ratio" in bm_map
    assert bm_map["cholesterol_hdl_ratio"]["value"] == 6.5
    assert bm_map["cholesterol_hdl_ratio"]["status"] == "High"

    assert "ldl_hdl_ratio" in bm_map
    assert bm_map["ldl_hdl_ratio"]["value"] == 4.3
    assert bm_map["ldl_hdl_ratio"]["status"] == "High"

    assert "apolipoprotein_a1" in bm_map
    assert bm_map["apolipoprotein_a1"]["value"] == 105.0
    assert bm_map["apolipoprotein_a1"]["status"] == "Low"

    assert "apolipoprotein_b" in bm_map
    assert bm_map["apolipoprotein_b"]["value"] == 140.0
    assert bm_map["apolipoprotein_b"]["status"] == "High"


def test_lipid_report_reference_range_preservation():
    """
    Test 4 & 5: Report-provided reference ranges are strictly preserved
    and determine biomarker status.
    """
    custom_ref_text = """
    LIPID PROFILE
    Serum Cholesterol 195 mg/dL 150 - 220
    Serum Triglycerides 160 mg/dL 50 - 200
    HDL Cholesterol 50 mg/dL 40 - 60
    """
    parsed = parse_lipid_profile_report(custom_ref_text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}

    # In generic rules, <200 is default, but report says 150 - 220
    assert bm_map["total_cholesterol"]["value"] == 195.0
    assert bm_map["total_cholesterol"]["reference_range"] == "150 - 220"
    assert bm_map["total_cholesterol"]["status"] == "Normal"
    assert bm_map["total_cholesterol"]["reference_source"] == "report"

    # In generic rules, <150 is default, but report says 50 - 200 -> 160 is Normal
    assert bm_map["triglycerides"]["value"] == 160.0
    assert bm_map["triglycerides"]["reference_range"] == "50 - 200"
    assert bm_map["triglycerides"]["status"] == "Normal"
    assert bm_map["triglycerides"]["reference_source"] == "report"


def test_lipid_profile_api_save_and_duplicate_flow():
    """
    Test 6-10: End-to-end API test verifying:
    - Save to Health Vault works with LIPID_PROFILE
    - Summary counts and status summary are dynamically accurate
    - Non-diagnostic educational explanations and patterns are generated
    - Report date is preserved
    - Duplicate detection returns 409 Conflict with original saved_at
    """
    db = SessionLocal()
    test_id = "test_lipid_vault_regression_001"
    file_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    try:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()

        analyzed_at = "2026-10-28T12:00:00+00:00"
        save_payload = {
            "request_id": test_id,
            "filename": "Lipid Profile Diagnostic Report.png",
            "report_type": "LIPID_PROFILE",
            "patient_gender": "male",
            "file_hash": file_hash,
            "analyzed_at": analyzed_at,
            "raw_parsed_report": {
                "report_date": "16 Oct 2026",
                "biomarkers": [
                    {
                        "key": "total_cholesterol",
                        "name": "Total Cholesterol",
                        "value": 235.0,
                        "unit": "mg/dL",
                        "reference_range": "<200",
                        "status": "High"
                    },
                    {
                        "key": "ldl",
                        "name": "LDL Cholesterol",
                        "value": 155.0,
                        "unit": "mg/dL",
                        "reference_range": "<100",
                        "status": "High"
                    },
                    {
                        "key": "hdl",
                        "name": "HDL Cholesterol",
                        "value": 36.0,
                        "unit": "mg/dL",
                        "reference_range": ">40",
                        "status": "Low"
                    },
                    {
                        "key": "triglycerides",
                        "name": "Triglycerides",
                        "value": 185.0,
                        "unit": "mg/dL",
                        "reference_range": "<150",
                        "status": "High"
                    }
                ],
                "metadata": {
                    "report": {"report_date": "16 Oct 2026"}
                }
            }
        }

        # 1. Save to Health Vault
        res = client.post("/api/v1/medical-reports/save-to-health-vault", json=save_payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["saved"] is True
        assert data["report_id"] == test_id
        assert data["report_date"] == "16 Oct 2026"
        assert data["abnormal_count"] == 4
        saved_at = data["saved_at"]
        assert saved_at is not None

        # 2. Retrieve via GET /api/v1/medical-reports/{report_id}
        get_res = client.get(f"/api/v1/medical-reports/{test_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["report_type"] == "LIPID_PROFILE"
        assert get_data["report_date"] == "16 Oct 2026"
        assert get_data["saved_at"] == saved_at

        # Verify explanation was generated deterministically without diagnosis
        report_data = get_data["report_data"]
        explanation = report_data.get("explanation", {})
        assert explanation is not None
        assert "disclaimer" in explanation

        # Verify pattern detection exists
        patterns = report_data.get("analysis", {}).get("patterns", [])
        pattern_ids = [p["pattern_id"] for p in patterns]
        assert "elevated_atherogenic_lipids" in pattern_ids
        assert "elevated_triglycerides" in pattern_ids
        assert "low_hdl" in pattern_ids

        # 3. Duplicate detection returns 409 Conflict with original saved_at
        dup_res = client.post("/api/v1/medical-reports/save-to-health-vault", json=save_payload)
        assert dup_res.status_code == 409
        dup_detail = dup_res.json()["detail"]
        assert dup_detail["existing_report_id"] == test_id
        assert dup_detail["saved_at"] == saved_at

    finally:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()
        db.close()


def test_apollo_lipid_profile_report_regression():
    """
    Focused regression test for the uploaded Apollo Diagnostics Lipid Profile report.
    Validates:
      - 2D spatial extraction aligns columns without row contamination
      - Correct lipid biomarker count (10 parameters)
      - Correct extracted values matching printed report (TC=248, TG=186, HDL=38, LDL=172, VLDL=37, Non-HDL=210, etc.)
      - Correct units and printed reference ranges preserved
      - Correct deterministic status flags
      - Pre-rule-engine internal consistency validation passes
      - Inconsistent mock lipid input triggers consistency warning without altering values
    """
    from app.services.lipid_consistency_service import validate_lipid_consistency

    # Spatial OCR lines corresponding to the Apollo Diagnostics report
    apollo_ocr_lines = [
        {"text": "Apollo Diagnostics", "confidence": 0.95, "bbox": [[114.0, 13.0], [392.0, 16.0], [392.0, 48.0], [113.0, 45.0]]},
        {"text": "Reported On : 22Sep202512:45PM", "confidence": 0.92, "bbox": [[456.0, 177.0], [751.0, 176.0], [751.0, 193.0], [456.0, 194.0]]},
        {"text": "LIPID PROFILE", "confidence": 0.98, "bbox": [[310.0, 246.0], [479.0, 246.0], [479.0, 269.0], [310.0, 269.0]]},
        {"text": "Test Name", "confidence": 0.95, "bbox": [[40.0, 289.0], [116.0, 289.0], [116.0, 309.0], [40.0, 309.0]]},
        {"text": "Result", "confidence": 0.95, "bbox": [[317.0, 288.0], [366.0, 288.0], [366.0, 309.0], [317.0, 309.0]]},
        {"text": "Unit", "confidence": 0.95, "bbox": [[433.0, 288.0], [469.0, 288.0], [469.0, 310.0], [433.0, 310.0]]},
        {"text": "Reference Range", "confidence": 0.95, "bbox": [[531.0, 287.0], [649.0, 289.0], [649.0, 310.0], [530.0, 308.0]]},
        {"text": "Flag", "confidence": 0.95, "bbox": [[697.0, 287.0], [735.0, 289.0], [734.0, 311.0], [696.0, 308.0]]},
        # Row 1: Total Cholesterol
        {"text": "Total Cholesterol", "confidence": 0.96, "bbox": [[40.0, 324.0], [152.0, 324.0], [152.0, 344.0], [40.0, 344.0]]},
        {"text": "248", "confidence": 0.99, "bbox": [[323.0, 323.0], [357.0, 323.0], [357.0, 345.0], [323.0, 345.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[409.0, 326.0], [459.0, 322.0], [461.0, 343.0], [411.0, 347.0]]},
        {"text": "<200", "confidence": 0.95, "bbox": [[531.0, 323.0], [575.0, 323.0], [575.0, 345.0], [531.0, 345.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 324.0], [735.0, 324.0], [735.0, 346.0], [696.0, 346.0]]},
        # Row 2: Triglycerides
        {"text": "Triglycerides", "confidence": 0.96, "bbox": [[40.0, 356.0], [126.0, 356.0], [126.0, 377.0], [40.0, 377.0]]},
        {"text": "186", "confidence": 0.99, "bbox": [[321.0, 356.0], [355.0, 353.0], [357.0, 375.0], [323.0, 377.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[409.0, 356.0], [459.0, 354.0], [461.0, 376.0], [411.0, 378.0]]},
        {"text": "<150", "confidence": 0.95, "bbox": [[529.0, 355.0], [574.0, 353.0], [575.0, 375.0], [530.0, 377.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 355.0], [735.0, 355.0], [735.0, 377.0], [696.0, 377.0]]},
        # Row 3: HDL Cholesterol
        {"text": "HDL Cholesterol", "confidence": 0.96, "bbox": [[40.0, 389.0], [146.0, 389.0], [146.0, 406.0], [40.0, 406.0]]},
        {"text": "38", "confidence": 0.99, "bbox": [[327.0, 387.0], [353.0, 387.0], [353.0, 408.0], [327.0, 408.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[411.0, 387.0], [460.0, 387.0], [460.0, 409.0], [411.0, 409.0]]},
        {"text": "> 40 (Male)", "confidence": 0.95, "bbox": [[530.0, 388.0], [610.0, 388.0], [610.0, 408.0], [530.0, 408.0]]},
        {"text": "Low", "confidence": 0.95, "bbox": [[696.0, 389.0], [732.0, 389.0], [732.0, 408.0], [696.0, 408.0]]},
        # Row 4: LDL Cholesterol (Calculated)
        {"text": "LDLCholesterol (Calculated)", "confidence": 0.96, "bbox": [[40.0, 421.0], [223.0, 421.0], [223.0, 438.0], [40.0, 438.0]]},
        {"text": "172", "confidence": 0.99, "bbox": [[324.0, 419.0], [356.0, 419.0], [356.0, 440.0], [324.0, 440.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[411.0, 419.0], [460.0, 419.0], [460.0, 441.0], [411.0, 441.0]]},
        {"text": "<100", "confidence": 0.95, "bbox": [[530.0, 419.0], [575.0, 419.0], [575.0, 440.0], [530.0, 440.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 419.0], [735.0, 419.0], [735.0, 441.0], [696.0, 441.0]]},
        # Row 5: VLDL Cholesterol (Calculated)
        {"text": "VLDLCholesterol (Calculated)", "confidence": 0.96, "bbox": [[40.0, 451.0], [233.0, 451.0], [233.0, 471.0], [40.0, 471.0]]},
        {"text": "37", "confidence": 0.99, "bbox": [[326.0, 450.0], [351.0, 450.0], [351.0, 471.0], [326.0, 471.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[409.0, 451.0], [459.0, 449.0], [461.0, 471.0], [411.0, 473.0]]},
        {"text": "5-40", "confidence": 0.95, "bbox": [[530.0, 450.0], [576.0, 450.0], [576.0, 471.0], [530.0, 471.0]]},
        {"text": "Normal", "confidence": 0.95, "bbox": [[697.0, 452.0], [750.0, 452.0], [750.0, 470.0], [697.0, 470.0]]},
        # Row 6: Non-HDL Cholesterol
        {"text": "Non-HDLCholesterol", "confidence": 0.96, "bbox": [[40.0, 484.0], [178.0, 484.0], [178.0, 501.0], [40.0, 501.0]]},
        {"text": "210", "confidence": 0.99, "bbox": [[323.0, 481.0], [357.0, 481.0], [357.0, 503.0], [323.0, 503.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[411.0, 482.0], [460.0, 482.0], [460.0, 504.0], [411.0, 504.0]]},
        {"text": "<130", "confidence": 0.95, "bbox": [[530.0, 481.0], [575.0, 481.0], [575.0, 503.0], [530.0, 503.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 482.0], [735.0, 482.0], [735.0, 504.0], [696.0, 504.0]]},
        # Row 7: TC/HDL Ratio
        {"text": "TC/HDL Ratio", "confidence": 0.96, "bbox": [[39.0, 514.0], [133.0, 514.0], [133.0, 534.0], [39.0, 534.0]]},
        {"text": "6.5", "confidence": 0.99, "bbox": [[324.0, 512.0], [355.0, 512.0], [355.0, 535.0], [324.0, 535.0]]},
        {"text": "Ratio", "confidence": 0.95, "bbox": [[411.0, 513.0], [453.0, 513.0], [453.0, 535.0], [411.0, 535.0]]},
        {"text": "< 5.0", "confidence": 0.95, "bbox": [[530.0, 513.0], [571.0, 513.0], [571.0, 535.0], [530.0, 535.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 513.0], [735.0, 513.0], [735.0, 536.0], [696.0, 536.0]]},
        # Row 8: LDL/HDL Ratio
        {"text": "LDL/HDL Ratio", "confidence": 0.96, "bbox": [[40.0, 545.0], [142.0, 545.0], [142.0, 565.0], [40.0, 565.0]]},
        {"text": "4.5", "confidence": 0.99, "bbox": [[324.0, 543.0], [355.0, 543.0], [355.0, 566.0], [324.0, 566.0]]},
        {"text": "Ratio", "confidence": 0.95, "bbox": [[411.0, 545.0], [453.0, 545.0], [453.0, 566.0], [411.0, 566.0]]},
        {"text": "<3.5", "confidence": 0.95, "bbox": [[530.0, 544.0], [571.0, 544.0], [571.0, 566.0], [530.0, 566.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 545.0], [735.0, 545.0], [735.0, 567.0], [696.0, 567.0]]},
        # Row 9: Apolipoprotein A1 (ApoA1)
        {"text": "Apolipoprotein A1 (ApoA1)", "confidence": 0.96, "bbox": [[40.0, 576.0], [220.0, 576.0], [220.0, 596.0], [40.0, 596.0]]},
        {"text": "110", "confidence": 0.99, "bbox": [[322.0, 577.0], [355.0, 577.0], [355.0, 596.0], [322.0, 596.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[409.0, 577.0], [459.0, 575.0], [461.0, 597.0], [411.0, 599.0]]},
        {"text": "100-220", "confidence": 0.95, "bbox": [[531.0, 576.0], [600.0, 576.0], [600.0, 597.0], [531.0, 597.0]]},
        {"text": "Normal", "confidence": 0.95, "bbox": [[697.0, 578.0], [751.0, 578.0], [751.0, 596.0], [697.0, 596.0]]},
        # Row 10: Apolipoprotein B (ApoB)
        {"text": "Apolipoprotein B (ApoB)", "confidence": 0.96, "bbox": [[40.0, 608.0], [202.0, 608.0], [202.0, 628.0], [40.0, 628.0]]},
        {"text": "145", "confidence": 0.99, "bbox": [[322.0, 607.0], [356.0, 607.0], [356.0, 629.0], [322.0, 629.0]]},
        {"text": "mg/dL", "confidence": 0.95, "bbox": [[412.0, 607.0], [460.0, 607.0], [460.0, 629.0], [412.0, 629.0]]},
        {"text": "<90", "confidence": 0.95, "bbox": [[530.0, 607.0], [568.0, 607.0], [568.0, 629.0], [530.0, 629.0]]},
        {"text": "High", "confidence": 0.95, "bbox": [[696.0, 605.0], [735.0, 607.0], [733.0, 630.0], [695.0, 628.0]]},
        {"text": "Comments / Interpretation:", "confidence": 0.95, "bbox": [[36.0, 666.0], [276.0, 666.0], [276.0, 686.0], [36.0, 686.0]]},
        {"text": "Total cholesterol, triglycerides, LDL cholesterol, non-HDL cholesterol and ApoB are elevated with low HDL cholesterol.", "confidence": 0.95, "bbox": [[35.0, 695.0], [744.0, 695.0], [744.0, 715.0], [35.0, 715.0]]}
    ]

    raw_text = "\n".join(l["text"] for l in apollo_ocr_lines)
    parsed = route_report_parser("LIPID_PROFILE", raw_text, ocr_lines=apollo_ocr_lines)

    assert parsed["report_type"] == "LIPID_PROFILE"
    assert parsed["parse_status"] == "success"
    assert len(parsed["biomarkers"]) == 10

    bm = {b["key"]: b for b in parsed["biomarkers"]}

    # Verify extracted parameters match printed values
    assert bm["total_cholesterol"]["value"] == 248.0
    assert bm["total_cholesterol"]["status"] == "High"
    assert bm["total_cholesterol"]["reference_range"] == "<200"

    assert bm["triglycerides"]["value"] == 186.0
    assert bm["triglycerides"]["status"] == "High"
    assert bm["triglycerides"]["reference_range"] == "<150"

    assert bm["hdl"]["value"] == 38.0
    assert bm["hdl"]["status"] == "Low"
    assert bm["hdl"]["reference_range"] == "> 40"

    assert bm["ldl"]["value"] == 172.0
    assert bm["ldl"]["status"] == "High"
    assert bm["ldl"]["reference_range"] == "<100"

    assert bm["vldl"]["value"] == 37.0
    assert bm["vldl"]["status"] == "Normal"
    assert bm["vldl"]["reference_range"] == "5 - 40"

    assert bm["non_hdl"]["value"] == 210.0
    assert bm["non_hdl"]["status"] == "High"
    assert bm["non_hdl"]["reference_range"] == "<130"

    assert bm["cholesterol_hdl_ratio"]["value"] == 6.5
    assert bm["cholesterol_hdl_ratio"]["status"] == "High"
    assert bm["cholesterol_hdl_ratio"]["reference_range"] == "< 5.0"

    assert bm["ldl_hdl_ratio"]["value"] == 4.5
    assert bm["ldl_hdl_ratio"]["status"] == "High"
    assert bm["ldl_hdl_ratio"]["reference_range"] == "<3.5"

    assert bm["apolipoprotein_a1"]["value"] == 110.0
    assert bm["apolipoprotein_a1"]["status"] == "Normal"
    assert bm["apolipoprotein_a1"]["reference_range"] == "100 - 220"

    assert bm["apolipoprotein_b"]["value"] == 145.0
    assert bm["apolipoprotein_b"]["status"] == "High"
    assert bm["apolipoprotein_b"]["reference_range"] == "<90"

    # Verify consistency checks pass on correct report values
    consistency_good = validate_lipid_consistency(parsed["biomarkers"])
    assert consistency_good["is_consistent"] is True
    assert len(consistency_good["warnings"]) == 0

    # Verify that an inconsistent mock set flags warnings WITHOUT altering values
    inconsistent_bms = [
        {"key": "total_cholesterol", "value": 186.0},
        {"key": "hdl", "value": 172.0},
        {"key": "ldl", "value": 37.0},
        {"key": "non_hdl", "value": 210.0},
        {"key": "cholesterol_hdl_ratio", "value": 4.5},
        {"key": "ldl_hdl_ratio", "value": 110.0}
    ]
    consistency_bad = validate_lipid_consistency(inconsistent_bms)
    assert consistency_bad["is_consistent"] is False
    assert len(consistency_bad["warnings"]) >= 3
    # Check that original values are not changed
    assert inconsistent_bms[0]["value"] == 186.0
    assert inconsistent_bms[1]["value"] == 172.0

