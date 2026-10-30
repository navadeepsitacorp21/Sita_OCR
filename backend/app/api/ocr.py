import io
import os
import re
import time
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.services.ocr_service import extract_text
from app.services.classifier_service import ClassifierService
from app.services.report_router import route_report_parser
from app.api.medical_reports import _enrich_biomarkers, MAX_FILE_SIZE_BYTES

logger = logging.getLogger("sita.ocr")
router = APIRouter(tags=["OCR Microservice"])

classifier_service = ClassifierService()

UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]


def validate_uuid(val: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate that val is a valid ABP User UUID (RFC 4122 format).
    Returns (is_valid, error_message).
    """
    if not val or not isinstance(val, str):
        return False, "user_id is required and must be a valid ABP User UUID."
    val_str = val.strip()
    try:
        parsed = uuid.UUID(val_str)
        # Verify 36-char hyphenated standard or 32-char hex
        if len(val_str) not in (32, 36):
            return False, f"Invalid user_id format '{val}'. Expected 36-character standard UUID."
        return True, None
    except (ValueError, AttributeError, TypeError):
        return False, f"Invalid user_id '{val}'. Must be a valid UUID (e.g. 8f7c1234-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."


def normalize_report_type_code(report_type: str) -> str:
    """Map canonical classifier keys to concise medical panel codes."""
    rt = (report_type or "").upper()
    if rt in ("LIVER_FUNCTION_TEST", "LFT"):
        return "LFT"
    if rt in ("KIDNEY_FUNCTION_TEST", "KFT", "RENAL_FUNCTION_TEST", "RFT"):
        return "KFT"
    if rt in ("COMPLETE_BLOOD_COUNT", "CBC"):
        return "CBC"
    if rt in ("LIPID_PROFILE", "LIPID"):
        return "LIPID"
    if rt in ("THYROID_PROFILE", "THYROID"):
        return "THYROID"
    if rt in ("DIABETES_PROFILE", "DIABETES_MONITORING", "HBA1C"):
        return "HBA1C"
    if rt in ("VITAMIN_PROFILE", "VITAMIN_PANEL", "VITAMIN"):
        return "VITAMIN"
    return rt or "UNKNOWN"


def structured_error_response(
    status_code: int,
    error_code: str,
    message: str,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
) -> JSONResponse:
    """Return a uniform, secure structured error response without exposing stack traces."""
    content = {
        "success": False,
        "user_id": user_id,
        "report_id": report_id,
        "error_code": error_code,
        "message": message,
    }
    return JSONResponse(status_code=status_code, content=content)


@router.post("/ocr/process")
@router.post("/ocr/analyze")
async def process_ocr_report(
    request: Request,
):
    """
    POST /api/v1/ocr/process & POST /api/v1/ocr/analyze

    Dedicated ABP OCR microservice endpoint:
    - Accepts an ABP User UUID (user_id) with every request.
    - Accepts medical report via multipart/form-data or JSON with base64 content.
    - Generates a unique report_id per report.
    - Executes RapidOCR ONNX pipeline + report classification + biomarker parsing.
    - Returns structured OCR results associating all biomarkers with user_id & report_id.
    - Completely stateless: no local DB persistence; designed for direct insertion by ABP/SITA backend into Supabase.
    """
    t_start = time.perf_counter()
    report_id = str(uuid.uuid4())

    user_id: Optional[str] = None
    filename: str = "medical_report.pdf"
    patient_gender: Optional[str] = None
    raw_bytes: bytes = b""

    content_type = request.headers.get("content-type", "")

    # ── 1. Parse Input Payload (JSON or multipart/form-data) ─────────────────
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            return structured_error_response(
                status_code=400,
                error_code="INVALID_PAYLOAD",
                message="Malformed JSON body.",
                report_id=report_id,
            )
        user_id = body.get("user_id")
        filename = body.get("filename") or "medical_report.pdf"
        patient_gender = body.get("patient_gender")

        file_content = body.get("file")
        if not file_content:
            return structured_error_response(
                status_code=400,
                error_code="FILE_REQUIRED",
                message="A medical report file is required in 'file' field.",
                user_id=user_id,
                report_id=report_id,
            )

        # Decode base64 if passed as string
        if isinstance(file_content, str):
            data_str = file_content
            if "," in data_str and "base64" in data_str:
                data_str = data_str.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(data_str)
            except Exception:
                return structured_error_response(
                    status_code=400,
                    error_code="CORRUPTED_FILE",
                    message="Failed to decode base64 file data.",
                    user_id=user_id,
                    report_id=report_id,
                )
        else:
            return structured_error_response(
                status_code=400,
                error_code="INVALID_PAYLOAD",
                message="The 'file' field in JSON request must be a base64 encoded string.",
                user_id=user_id,
                report_id=report_id,
            )
    else:
        # Multipart form data
        try:
            form = await request.form()
        except Exception:
            return structured_error_response(
                status_code=400,
                error_code="INVALID_PAYLOAD",
                message="Could not parse multipart form data.",
                report_id=report_id,
            )
        user_id = form.get("user_id")
        patient_gender = form.get("patient_gender")

        uploaded_file = form.get("file")
        if not uploaded_file:
            return structured_error_response(
                status_code=400,
                error_code="FILE_REQUIRED",
                message="A medical report file is required in 'file' form-data.",
                user_id=user_id,
                report_id=report_id,
            )

        if hasattr(uploaded_file, "filename"):
            filename = uploaded_file.filename or filename
            try:
                raw_bytes = await uploaded_file.read()
            except Exception:
                return structured_error_response(
                    status_code=400,
                    error_code="FILE_READ_FAILED",
                    message="Could not read uploaded file content.",
                    user_id=user_id,
                    report_id=report_id,
                )
        elif isinstance(uploaded_file, (bytes, bytearray)):
            raw_bytes = bytes(uploaded_file)
        else:
            return structured_error_response(
                status_code=400,
                error_code="FILE_REQUIRED",
                message="Invalid file upload object.",
                user_id=user_id,
                report_id=report_id,
            )

    # ── 2. Validate ABP User UUID ──────────────────────────────────────────
    is_valid_uuid, uuid_err = validate_uuid(user_id)
    if not is_valid_uuid:
        return structured_error_response(
            status_code=400,
            error_code="INVALID_USER_ID",
            message=uuid_err or "A valid ABP User UUID is required.",
            user_id=user_id,
            report_id=report_id,
        )

    # ── 3. Validate File Format & Size ─────────────────────────────────────
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return structured_error_response(
            status_code=400,
            error_code="INVALID_FILE_FORMAT",
            message="Unsupported file format. Please upload a PDF, PNG, JPG, JPEG, or WEBP file.",
            user_id=user_id,
            report_id=report_id,
        )

    if not raw_bytes:
        return structured_error_response(
            status_code=400,
            error_code="EMPTY_FILE",
            message="The uploaded file is empty.",
            user_id=user_id,
            report_id=report_id,
        )

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        return structured_error_response(
            status_code=413,
            error_code="FILE_TOO_LARGE",
            message=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
            user_id=user_id,
            report_id=report_id,
        )

    # Magic byte verification
    is_pdf = raw_bytes[:4] == b"%PDF"
    is_png = raw_bytes[:4] == b"\x89PNG"
    is_jpg = raw_bytes[:3] in (b"\xff\xd8\xff",)
    is_webp = raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP"
    ext = next((e for e in ALLOWED_EXTENSIONS if filename_lower.endswith(e)), "")

    if (
        (ext == ".pdf" and not is_pdf)
        or (ext == ".png" and not is_png)
        or (ext in (".jpg", ".jpeg") and not is_jpg)
        or (ext == ".webp" and not is_webp)
    ):
        return structured_error_response(
            status_code=400,
            error_code="CORRUPTED_FILE",
            message="The uploaded file content does not match its file extension or is corrupted.",
            user_id=user_id,
            report_id=report_id,
        )

    # ── 4. OCR Processing Pipeline ─────────────────────────────────────────
    t_file_prep_start = time.perf_counter()
    wrapped_file = StarletteUploadFile(
        filename=filename,
        file=io.BytesIO(raw_bytes),
    )
    file_prep_ms = (time.perf_counter() - t_file_prep_start) * 1000

    try:
        ocr_result = await extract_text(wrapped_file, request_id=report_id)
    except Exception as exc:
        logger.error("[%s] OCR extraction error: %s", report_id, exc, exc_info=True)
        return structured_error_response(
            status_code=422,
            error_code="OCR_PROCESSING_FAILED",
            message=f"Failed to process document with OCR engine: {str(exc)}",
            user_id=user_id,
            report_id=report_id,
        )

    ocr_text = ocr_result.get("text", "")
    ocr_lines = ocr_result.get("ocr_lines", [])
    perf_meta = ocr_result.get("performance", {})

    if not ocr_text or not ocr_text.strip():
        return structured_error_response(
            status_code=422,
            error_code="OCR_PROCESSING_FAILED",
            message="Unable to extract readable text from the uploaded report.",
            user_id=user_id,
            report_id=report_id,
        )

    # ── 5. Classification & Report Parsing ────────────────────────────────
    t_parse_start = time.perf_counter()
    classification = classifier_service.classify_report(ocr_text)
    detected_type = classification.get("report_type") or "UNKNOWN"
    parsed_report = route_report_parser(
        detected_type,
        ocr_text,
        ocr_lines=ocr_lines,
    )
    parsing_time_ms = (time.perf_counter() - t_parse_start) * 1000

    # ── 6. Biomarker Extraction & Rule Engine Enrichment ──────────────────
    t_val_start = time.perf_counter()
    raw_biomarkers = parsed_report.get("biomarkers", [])

    raw_meta = parsed_report.get("metadata") or {}
    report_meta = parsed_report.get("report") or raw_meta.get("report") or {}
    patient_meta = parsed_report.get("patient") or raw_meta.get("patient") or {}

    report_date = (
        parsed_report.get("report_date")
        or report_meta.get("report_date")
        or report_meta.get("collection_date")
        or report_meta.get("reported_date")
        or report_meta.get("received_date")
        or report_meta.get("ordered_date")
    )
    collection_date = report_meta.get("collection_date")
    reported_date = report_meta.get("reported_date")
    report_interpretation = (
        parsed_report.get("report_interpretation")
        or report_meta.get("report_interpretation")
        or raw_meta.get("report_interpretation")
    )

    # Patient gender determination
    report_patient_gender = (patient_meta.get("gender") or "").strip().lower()
    gender_to_use = (patient_gender or report_patient_gender or "unknown").strip().lower()

    enriched_biomarkers = _enrich_biomarkers(raw_biomarkers, gender_to_use)
    validation_time_ms = (time.perf_counter() - t_val_start) * 1000

    # ── 7. Construct User-Associated Structured Response ───────────────────
    created_at_iso = datetime.now(timezone.utc).isoformat()
    total_time_ms = round((time.perf_counter() - t_start) * 1000, 1)
    normalized_type = normalize_report_type_code(detected_type)
    avg_confidence = ocr_result.get("average_confidence", 1.0)

    # Build biomarkers conforming to Section 5 & 7
    biomarkers_out: List[Dict[str, Any]] = []
    for bm in enriched_biomarkers:
        raw_val = bm.get("value")
        num_val = float(raw_val) if isinstance(raw_val, (int, float)) else raw_val

        ref_min = bm.get("lower_limit")
        ref_max = bm.get("upper_limit")
        ref_text = bm.get("reference_range") or ""
        ref_source = bm.get("reference_source") or "report"

        st = str(bm.get("status") or "normal").lower()
        conf = bm.get("confidence")
        if conf is None:
            conf = avg_confidence
        conf = round(float(conf), 2)

        biomarkers_out.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "report_id": report_id,
            "name": bm.get("name") or bm.get("key", "").replace("_", " ").title(),
            "value": num_val,
            "unit": bm.get("unit") or "",
            "reference_min": ref_min,
            "reference_max": ref_max,
            "reference_text": ref_text,
            "reference_source": ref_source,
            "status": st,
            "confidence": conf,
            "created_at": created_at_iso,
        })

        overall_st = "normal"
        abnormal_cnt = sum(1 for b in biomarkers_out if b.get("status") in ("high", "low", "above range", "below range", "needs review"))
        if abnormal_cnt > 0:
            overall_st = "needs_review"

        # Build report record conforming to Section 4 (Structured metadata only, no file storage references)
        report_record = {
            "id": report_id,
            "report_id": report_id,
            "user_id": user_id,
            "report_type": normalized_type,
            "report_date": report_date,
            "collection_date": collection_date,
            "reported_date": reported_date,
            "ocr_status": "completed",
            "page_count": ocr_result.get("page_count", 1),
            "overall_status": overall_st,
            "abnormal_count": abnormal_cnt,
            "analyzed_at": created_at_iso,
            "created_at": created_at_iso,
        }

    logger.info(
        "[ABP-OCR] user_id=%s report_id=%s report_type=%s biomarkers=%d total_ms=%.1f",
        user_id,
        report_id,
        normalized_type,
        len(biomarkers_out),
        total_time_ms,
    )

    return {
        "success": True,
        "user_id": user_id,
        "report_id": report_id,
        "report_type": normalized_type,
        "report_interpretation": report_interpretation,
        "processing_status": "completed",
        "processing_time_ms": int(total_time_ms),
        "report": report_record,
        "biomarkers": biomarkers_out,
        "performance": {
            "file_processing_time_ms": round(file_prep_ms, 1),
            "ocr_inference_time_ms": round(perf_meta.get("ocr_inference_ms", 0.0), 1),
            "parsing_time_ms": round(parsing_time_ms, 1),
            "validation_time_ms": round(validation_time_ms, 1),
            "total_processing_time_ms": total_time_ms,
        },
    }
