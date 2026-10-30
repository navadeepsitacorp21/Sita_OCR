import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "ocr")


@pytest.fixture
def client():
    return TestClient(app)


def test_original_care_diagnostics_lft_production_flow(client):
    """
    Hospital-grade deterministic end-to-end production flow test for Care Diagnostics LFT.
    Simulates the exact HTTP multipart upload payload used by the UI.
    Validates:
    - HTTP 200 OK
    - Report Classification: LIVER_FUNCTION_TEST
    - Authoritative Parser Version: 1.3.2
    - Biomarker count: exactly 12
    - GGT extracted with value=28.0, unit='U/L', status='Normal'
    - Reference bounds (<55, <38) NEVER incorrectly extracted as observed values
    - Health Vault persistence succeeded and report retrieved via GET matches exactly
    """
    image_path = os.path.join(FIXTURES_DIR, "original_care_diagnostics_lft.png")
    assert os.path.exists(image_path), f"Original screenshot fixture missing: {image_path}"

    report_id = None
    try:
        with open(image_path, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("original_care_diagnostics_lft.png", f, "image/png")}
            )

        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()

        # 1. Top-level structure
        assert data["classification"]["report_type"] == "LIVER_FUNCTION_TEST"
        parsed_report = data["parsed_report"]
        assert parsed_report["parser_version"] == "1.3.2"
        assert parsed_report["biomarkers_found"] == 12
        assert len(parsed_report["biomarkers_missing"]) == 0

        # 2. Biomarkers map
        bm_map = {b["key"]: b for b in parsed_report["biomarkers"]}
        assert len(bm_map) == 12

        # Verify all 12 biomarkers with exact values
        assert bm_map["total_bilirubin"]["value"] == 0.8
        assert bm_map["total_bilirubin"]["unit"] == "mg/dL"
        assert bm_map["total_bilirubin"]["status"] == "Normal"

        assert bm_map["direct_bilirubin"]["value"] == 0.2
        assert bm_map["direct_bilirubin"]["unit"] == "mg/dL"
        assert bm_map["direct_bilirubin"]["status"] == "Normal"

        assert bm_map["indirect_bilirubin"]["value"] == 0.6
        assert bm_map["indirect_bilirubin"]["unit"] == "mg/dL"
        assert bm_map["indirect_bilirubin"]["status"] == "Normal"

        assert bm_map["alt_sgpt"]["value"] == 32.0
        assert bm_map["alt_sgpt"]["unit"] == "U/L"
        assert bm_map["alt_sgpt"]["status"] == "Normal"

        assert bm_map["ast_sgot"]["value"] == 29.0
        assert bm_map["ast_sgot"]["unit"] == "U/L"
        assert bm_map["ast_sgot"]["status"] == "Normal"

        assert bm_map["alkaline_phosphatase"]["value"] == 94.0
        assert bm_map["alkaline_phosphatase"]["unit"] == "U/L"
        assert bm_map["alkaline_phosphatase"]["status"] == "Normal"

        # GGT validation
        assert "ggt" in bm_map
        assert bm_map["ggt"]["value"] == 28.0
        assert bm_map["ggt"]["unit"] == "U/L"
        assert bm_map["ggt"]["status"] == "Normal"
        assert bm_map["ggt"]["value"] != 38.0
        assert bm_map["ggt"]["value"] != 55.0
        assert bm_map["ggt"]["value"] != 7.2

        assert bm_map["total_protein"]["value"] == 7.2
        assert bm_map["total_protein"]["unit"] == "g/dL"
        assert bm_map["total_protein"]["status"] == "Normal"

        assert bm_map["albumin"]["value"] == 4.5
        assert bm_map["albumin"]["unit"] == "g/dL"
        assert bm_map["albumin"]["status"] == "Normal"

        assert bm_map["globulin"]["value"] == 2.7
        assert bm_map["globulin"]["unit"] == "g/dL"
        assert bm_map["globulin"]["status"] == "Normal"

        assert bm_map["albumin_globulin_ratio"]["value"] == 1.67
        assert bm_map["albumin_globulin_ratio"]["unit"] == "ratio"
        assert bm_map["albumin_globulin_ratio"]["status"] == "Normal"

        assert bm_map["ldh"]["value"] == 210.0
        assert bm_map["ldh"]["unit"] == "U/L"
        assert bm_map["ldh"]["status"] == "Normal"

        # Health summary
        health_summary = data["health_summary"]
        assert health_summary["overall_status"] == "Healthy"
        assert health_summary["abnormal_count"] == 0
        assert health_summary["normal_biomarkers"] == 12

        # 3. Health Vault verification
        vault_info = data.get("health_vault", {})
        assert vault_info.get("saved") is True
        report_id = vault_info.get("report_id")
        assert report_id is not None

        vault_res = client.get(f"/api/v1/health-vault/reports/{report_id}")
        assert vault_res.status_code == 200
        vault_data = vault_res.json()
        vault_bms = vault_data["report"]["parsed_report"]["biomarkers"]
        assert len(vault_bms) == 12
        vault_bm_map = {b["key"]: b for b in vault_bms}
        assert vault_bm_map["ggt"]["value"] == 28.0
        assert vault_bm_map["ggt"]["unit"] == "U/L"
        assert vault_bm_map["ggt"]["status"] == "Normal"
    finally:
        if report_id:
            from app.database import HealthReport, SessionLocal
            db = SessionLocal()
            try:
                db.query(HealthReport).filter(HealthReport.report_id == report_id).delete()
                db.commit()
            finally:
                db.close()
