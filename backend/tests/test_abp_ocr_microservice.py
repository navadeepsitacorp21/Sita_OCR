import os
import uuid
import base64
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "ocr")
LFT_FIXTURE = os.path.join(FIXTURES_DIR, "original_care_diagnostics_lft.png")
CBC_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "3.webp")


# ── 1. User Association Tests ────────────────────────────────────────────────

def test_abp_user_uuid_returned_unchanged_multipart():
    """
    Requirement 1:
    Request contains valid ABP User UUID → UUID returned unchanged.
    """
    user_uuid = str(uuid.uuid4())
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/ocr/process",
            data={"user_id": user_uuid},
            files={"file": ("original_care_diagnostics_lft.png", f, "image/png")},
        )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["user_id"] == user_uuid
    assert data["processing_status"] == "completed"
    assert "report_id" in data
    assert "report" in data
    assert data["report"]["user_id"] == user_uuid


def test_abp_user_uuid_json_base64():
    """
    Requirement 1 & Microservice Target:
    Request contains ABP User UUID and base64 encoded file in JSON body.
    """
    user_uuid = str(uuid.uuid4())
    with open(LFT_FIXTURE, "rb") as f:
        b64_content = base64.b64encode(f.read()).decode("utf-8")

    res = client.post(
        "/api/v1/ocr/process",
        json={
            "user_id": user_uuid,
            "file": b64_content,
            "filename": "original_care_diagnostics_lft.png",
        },
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["user_id"] == user_uuid
    assert data["report_type"] == "LFT"
    assert len(data["biomarkers"]) >= 10


# ── 2. Report Identification & Uniqueness ────────────────────────────────────

def test_report_id_unique_per_request():
    """
    Requirement 2 & 15:
    Each request receives a unique report_id.
    """
    user_uuid = str(uuid.uuid4())
    with open(LFT_FIXTURE, "rb") as f:
        img_bytes = f.read()

    res1 = client.post(
        "/api/v1/ocr/process",
        data={"user_id": user_uuid},
        files={"file": ("lft_1.png", img_bytes, "image/png")},
    )
    res2 = client.post(
        "/api/v1/ocr/process",
        data={"user_id": user_uuid},
        files={"file": ("lft_2.png", img_bytes, "image/png")},
    )

    assert res1.status_code == 200
    assert res2.status_code == 200

    report_id_1 = res1.json()["report_id"]
    report_id_2 = res2.json()["report_id"]

    assert report_id_1 is not None
    assert report_id_2 is not None
    # Must be valid UUIDs
    uuid.UUID(report_id_1)
    uuid.UUID(report_id_2)
    # Same user, different reports -> different report_ids
    assert report_id_1 != report_id_2


# ── 3. Biomarker Association with User UUID and Report ID ────────────────────

def test_biomarker_association():
    """
    Requirement 7:
    Every biomarker must contain user_id and report_id matching the request and report.
    """
    user_uuid = str(uuid.uuid4())
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/ocr/process",
            data={"user_id": user_uuid},
            files={"file": ("original_care_diagnostics_lft.png", f, "image/png")},
        )

    assert res.status_code == 200
    data = res.json()
    report_id = data["report_id"]
    biomarkers = data["biomarkers"]
    assert len(biomarkers) == 12

    for bm in biomarkers:
        assert bm["user_id"] == user_uuid
        assert bm["report_id"] == report_id
        assert "name" in bm
        assert "value" in bm
        assert "unit" in bm
        assert "status" in bm
        assert "confidence" in bm
        assert "reference_min" in bm
        assert "reference_max" in bm
        assert "created_at" in bm
        # ID must be present
        uuid.UUID(bm["id"])


# ── 4. Supabase Contract Compatibility ────────────────────────────────────────

def test_supabase_contract_compatibility():
    """
    Requirement 6 & 7:
    Verify that the response contains all required fields for Supabase
    'medical_reports' and 'biomarkers' tables.
    """
    user_uuid = str(uuid.uuid4())
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/ocr/process",
            data={"user_id": user_uuid},
            files={"file": ("lft.png", f, "image/png")},
        )

    assert res.status_code == 200
    data = res.json()

    # medical_reports schema fields (strictly structured metadata, no storage_path or file_reference)
    rep = data["report"]
    assert rep["id"] == data["report_id"]
    assert rep["report_id"] == data["report_id"]
    assert rep["user_id"] == user_uuid
    assert rep["report_type"] in ("LFT", "LIVER_FUNCTION_TEST")
    assert "report_date" in rep
    assert "collection_date" in rep
    assert "reported_date" in rep
    assert "overall_status" in rep
    assert "abnormal_count" in rep
    assert "analyzed_at" in rep
    assert rep["ocr_status"] == "completed"
    assert "created_at" in rep
    assert "storage_path" not in rep
    assert "file_reference" not in rep

    # biomarkers schema fields
    for bm in data["biomarkers"]:
        assert "id" in bm
        assert bm["user_id"] == user_uuid
        assert bm["report_id"] == rep["id"]
        assert "name" in bm
        assert "value" in bm
        assert "unit" in bm
        assert "reference_min" in bm
        assert "reference_max" in bm
        assert "reference_text" in bm
        assert "reference_source" in bm
        assert "status" in bm
        assert "confidence" in bm
        assert "created_at" in bm


# ── 5. Invalid User ID & Validation Error Tests ──────────────────────────────

def test_missing_user_id_fails():
    """
    Requirement 10 & 15:
    Missing user_id returns structured 400 error.
    """
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/ocr/process",
            files={"file": ("lft.png", f, "image/png")},
        )

    assert res.status_code == 400
    err = res.json()
    assert err["success"] is False
    assert err["error_code"] == "INVALID_USER_ID"


def test_invalid_uuid_fails():
    """
    Requirement 10 & 15:
    Non-UUID user_id returns structured 400 error without exposing stack traces.
    """
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/ocr/process",
            data={"user_id": "not-a-valid-uuid"},
            files={"file": ("lft.png", f, "image/png")},
        )

    assert res.status_code == 400
    err = res.json()
    assert err["success"] is False
    assert err["error_code"] == "INVALID_USER_ID"
    assert err["user_id"] == "not-a-valid-uuid"


def test_empty_file_fails():
    """
    Requirement 4 & 11:
    Empty file returns structured 400 error.
    """
    user_uuid = str(uuid.uuid4())
    res = client.post(
        "/api/v1/ocr/process",
        data={"user_id": user_uuid},
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert res.status_code == 400
    err = res.json()
    assert err["success"] is False
    assert err["error_code"] == "EMPTY_FILE"


def test_unsupported_file_format_fails():
    """
    Requirement 4 & 11:
    Unsupported extension returns structured 400 error.
    """
    user_uuid = str(uuid.uuid4())
    res = client.post(
        "/api/v1/ocr/process",
        data={"user_id": user_uuid},
        files={"file": ("report.exe", b"MZtest", "application/octet-stream")},
    )
    assert res.status_code == 400
    err = res.json()
    assert err["success"] is False
    assert err["error_code"] == "INVALID_FILE_FORMAT"


# ── 6. Backward Compatibility on /medical-reports/analyze ────────────────────

def test_medical_reports_analyze_with_user_id():
    """
    Requirement 14:
    /medical-reports/analyze also accepts user_id and enriches response with user_id and report_id.
    """
    user_uuid = str(uuid.uuid4())
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/medical-reports/analyze",
            data={"user_id": user_uuid},
            files={"file": ("care_lft.png", f, "image/png")},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["user_id"] == user_uuid
    assert data["report_id"] is not None
    assert len(data["biomarkers"]) == 12
    for bm in data["biomarkers"]:
        assert bm["user_id"] == user_uuid
        assert bm["report_id"] == data["report_id"]


def test_medical_reports_analyze_without_user_id_backward_compatible():
    """
    Requirement 14:
    /medical-reports/analyze without user_id continues working with 100% backward compatibility.
    """
    with open(LFT_FIXTURE, "rb") as f:
        res = client.post(
            "/api/v1/medical-reports/analyze",
            files={"file": ("care_lft_compat.png", f, "image/png")},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["report_type"] == "LIVER_FUNCTION_TEST"
    assert data["user_id"] is None
    assert len(data["biomarkers"]) == 12


# ── 7. Multi-Report Type Support Verification ────────────────────────────────

def test_multi_report_support_kft():
    """
    Verify KFT report is identified, routed, parsed, and produces the generic schema.
    """
    kft_fixture = os.path.join(FIXTURES_DIR, "original_care_diagnostics_kft.png")
    if not os.path.exists(kft_fixture):
        pytest.skip("KFT fixture not available")

    user_uuid = str(uuid.uuid4())
    with open(kft_fixture, "rb") as f:
        res = client.post(
            "/api/v1/ocr/process",
            data={"user_id": user_uuid},
            files={"file": ("care_kft.png", f, "image/png")},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["report_type"] == "KFT"
    assert data["report"]["report_type"] == "KFT"
    assert data["report"]["user_id"] == user_uuid
    assert len(data["biomarkers"]) > 0
    for bm in data["biomarkers"]:
        assert bm["user_id"] == user_uuid
        assert bm["report_id"] == data["report_id"]
        assert "name" in bm
        assert "value" in bm
        assert "unit" in bm


