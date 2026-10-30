import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import SessionLocal
from app.database.models import HealthReport, to_utc_iso

client = TestClient(app)


def test_analyze_endpoint_returns_analyzed_at_and_null_saved_at():
    """
    Case 1: When a report is analyzed, it must return an authoritative analyzed_at
    timestamp, while saved_at and saved_to_vault_at MUST be None/null.
    """
    with open("backend/tests/fixtures/ocr/aster_cbc.png", "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/medical-reports/analyze",
        files={"file": ("aster_cbc.png", file_bytes, "image/png")},
        data={"patient_gender": "male"}
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["success"] is True
    assert data["analyzed_at"] is not None
    assert "T" in data["analyzed_at"]
    # Saved timestamp MUST be None before explicit Health Vault save
    assert data["saved_at"] is None
    assert data["saved_to_vault_at"] is None
    assert data["metadata"]["saved_at"] is None
    assert data["metadata"]["saved_to_vault_at"] is None


def test_save_to_health_vault_timestamps_and_ordering():
    """
    Case 2: When saving to Health Vault, saved_at is generated, persisted,
    and guaranteed to satisfy analyzed_at <= saved_at.
    """
    db = SessionLocal()
    test_id = "test_timestamp_ordering_001"
    file_hash = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    try:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()

        analyzed_at_dt = datetime(2026, 10, 28, 10, 44, 0, tzinfo=timezone.utc)
        analyzed_at_str = analyzed_at_dt.isoformat()

        save_payload = {
            "request_id": test_id,
            "filename": "test_cbc.png",
            "report_type": "CBC",
            "patient_gender": "male",
            "file_hash": file_hash,
            "analyzed_at": analyzed_at_str,
            "raw_parsed_report": {
                "report_date": "08 Sept 2025",
                "biomarkers": [
                    {
                        "name": "Hemoglobin",
                        "value": 14.5,
                        "unit": "g/dL",
                        "key": "hemoglobin",
                        "reference_range": "13.0 - 17.0"
                    }
                ]
            }
        }

        save_res = client.post("/api/v1/medical-reports/save-to-health-vault", json=save_payload)
        assert save_res.status_code == 200, save_res.text
        save_data = save_res.json()

        assert save_data["saved"] is True
        saved_at_str = save_data["saved_at"]
        assert saved_at_str is not None
        assert save_data["saved_to_vault_at"] == saved_at_str
        assert save_data["analyzed_at"] == analyzed_at_str

        # Verify logical ordering: analyzed_at <= saved_at
        saved_at_dt = datetime.fromisoformat(saved_at_str.replace("Z", "+00:00"))
        assert analyzed_at_dt <= saved_at_dt

        # Ensure explicit UTC offset is included (e.g. +00:00 or Z)
        assert saved_at_str.endswith("Z") or "+00:00" in saved_at_str

        # Verify DB persistence
        rep = db.query(HealthReport).filter_by(report_id=test_id).first()
        assert rep is not None
        assert rep.saved_at is not None
        assert rep.saved_at_iso == saved_at_str

    finally:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()
        db.close()


def test_consistent_timestamps_across_get_endpoints():
    """
    Case 3: All GET endpoints (medical-reports, health-vault detail, timeline)
    return consistent, normalized UTC ISO timestamps.
    """
    db = SessionLocal()
    test_id = "test_timestamp_consistency_002"
    file_hash = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
    try:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()

        analyzed_at_str = "2026-10-28T10:44:00+00:00"
        save_payload = {
            "request_id": test_id,
            "filename": "test_lft.png",
            "report_type": "LIVER_FUNCTION_TEST",
            "patient_gender": "male",
            "file_hash": file_hash,
            "analyzed_at": analyzed_at_str,
            "raw_parsed_report": {
                "report_date": "15/06/2024",
                "biomarkers": [
                    {
                        "name": "Bilirubin Total",
                        "value": 0.8,
                        "unit": "mg/dL",
                        "key": "bilirubin_total",
                        "reference_range": "0.2 - 1.2"
                    }
                ]
            }
        }

        save_res = client.post("/api/v1/medical-reports/save-to-health-vault", json=save_payload)
        assert save_res.status_code == 200
        saved_at_str = save_res.json()["saved_at"]

        # 1. GET /api/v1/medical-reports/{report_id}
        res1 = client.get(f"/api/v1/medical-reports/{test_id}")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["report_date"] == "15/06/2024"
        assert data1["analyzed_at"] == analyzed_at_str
        assert data1["saved_at"] == saved_at_str

        # 2. GET /api/v1/health-vault/reports/{report_id}
        res2 = client.get(f"/api/v1/health-vault/reports/{test_id}")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["saved_at"] == saved_at_str
        assert data2["analyzed_at"] == analyzed_at_str

        # 3. GET /api/v1/health-vault/reports (timeline list)
        res3 = client.get("/api/v1/health-vault/reports")
        assert res3.status_code == 200
        data3 = res3.json()
        matched = next((r for r in data3["reports"] if r["report_id"] == test_id), None)
        assert matched is not None
        assert matched["saved_at"] == saved_at_str
        assert matched["analyzed_at"] == analyzed_at_str
        assert matched["report_date"] == "15/06/2024"

    finally:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()
        db.close()


def test_failed_save_does_not_persist():
    """
    Case 4: A failed save request (e.g. invalid report type or empty biomarkers)
    must fail without persisting any saved timestamp.
    """
    db = SessionLocal()
    test_id = "test_timestamp_failed_save_003"
    try:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()

        bad_payload = {
            "request_id": test_id,
            "filename": "invalid.png",
            "report_type": "UNSUPPORTED_TYPE_XYZ",
            "patient_gender": "male",
            "file_hash": "badhash123",
            "analyzed_at": "2026-10-28T12:00:00+00:00",
            "raw_parsed_report": {
                "biomarkers": []
            }
        }
        res = client.post("/api/v1/medical-reports/save-to-health-vault", json=bad_payload)
        assert res.status_code == 400

        # Verify nothing persisted in DB
        rep = db.query(HealthReport).filter_by(report_id=test_id).first()
        assert rep is None

    finally:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()
        db.close()


def test_duplicate_save_preserves_original_timestamp():
    """
    Case 5: Duplicate save returns 409 Conflict with the original saved_at
    timestamp and does NOT overwrite or generate a new timestamp.
    """
    db = SessionLocal()
    test_id = "test_timestamp_dup_004"
    file_hash = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
    try:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()

        save_payload = {
            "request_id": test_id,
            "filename": "test_kft.png",
            "report_type": "KIDNEY_FUNCTION_TEST",
            "patient_gender": "male",
            "file_hash": file_hash,
            "analyzed_at": "2026-10-28T10:00:00+00:00",
            "raw_parsed_report": {
                "report_date": "02/12/2022",
                "biomarkers": [
                    {"name": "Urea", "value": 25.0, "unit": "mg/dL", "key": "urea"}
                ]
            }
        }

        # First save
        res1 = client.post("/api/v1/medical-reports/save-to-health-vault", json=save_payload)
        assert res1.status_code == 200
        original_saved_at = res1.json()["saved_at"]

        # Second save (duplicate)
        res2 = client.post("/api/v1/medical-reports/save-to-health-vault", json=save_payload)
        assert res2.status_code == 409
        detail = res2.json()["detail"]
        assert detail["existing_report_id"] == test_id
        assert detail["saved_at"] == original_saved_at

        # Verify DB still has original timestamp
        rep = db.query(HealthReport).filter_by(report_id=test_id).first()
        assert rep.saved_at_iso == original_saved_at

    finally:
        db.query(HealthReport).filter_by(report_id=test_id).delete()
        db.commit()
        db.close()


def test_to_utc_iso_helper():
    """
    Case 6: to_utc_iso correctly normalizes naive datetimes, timezone-aware datetimes,
    and string representations.
    """
    # Naive datetime
    naive = datetime(2026, 10, 28, 10, 45, 0)
    iso_naive = to_utc_iso(naive)
    assert iso_naive.endswith("+00:00") or iso_naive.endswith("Z")

    # Timezone-aware datetime
    aware = datetime(2026, 10, 28, 10, 45, 0, tzinfo=timezone.utc)
    iso_aware = to_utc_iso(aware)
    assert "+00:00" in iso_aware

    # Naive string without Z
    str_naive = "2026-10-28 10:45:00"
    iso_str = to_utc_iso(str_naive)
    assert iso_str == "2026-10-28T10:45:00Z"

    # None
    assert to_utc_iso(None) is None
