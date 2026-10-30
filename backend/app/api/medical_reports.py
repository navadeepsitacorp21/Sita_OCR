import hashlib
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, create_report, get_report, get_report_by_hash
from app.database.models import to_utc_iso
from app.services.ocr_service import extract_text
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.services.medical_rule_engine import (
    interpret_biomarker,
    detect_cross_biomarker_patterns,
    generate_deterministic_report_summary,
)
from app.services.trend_service import compute_biomarker_trends
from app.services.status_engine import calculate_status
from app.services.medical_explanation_engine import generate_medical_explanation

logger = logging.getLogger("sita.medical_analysis")
router = APIRouter(tags=["Medical Report Analysis"])

# ──────────────────────────────────────────────────────────
# Rule-engine version – bump this whenever interpretation
# rules or pattern logic materially change.
# ──────────────────────────────────────────────────────────
RULE_ENGINE_VERSION = "1.0.0"
RULE_ENGINE_NAME = "deterministic_medical_rule_engine"

SUPPORTED_REPORT_TYPES = ["CBC", "LIVER_FUNCTION_TEST", "KIDNEY_FUNCTION_TEST", "LIPID_PROFILE"]

# Maximum acceptable upload size: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

def _sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of raw file bytes."""
    return hashlib.sha256(data).hexdigest()


def _enrich_biomarkers(
    raw_biomarkers: List[Dict[str, Any]],
    gender_to_use: str,
) -> List[Dict[str, Any]]:
    """
    Server-side deterministic enrichment: applies the medical rule engine to each
    biomarker and returns the fully structured list.  This is the single source of
    truth for statuses, patterns, and explanations — it is always executed on the
    backend and never reconstructed from a client-supplied payload.
    """
    enriched: List[Dict[str, Any]] = []
    for bm in raw_biomarkers:
        key = bm.get("key", "")
        status = bm.get("status", "Unknown")
        val = bm.get("value")
        unit = bm.get("unit") or bm.get("display_unit") or ""
        ref_range = bm.get("reference_range", "")
        s_ref = bm.get("structured_reference") or {}
        ref_type = s_ref.get("type") or "range"
        ref_source = bm.get("reference_source", "none")

        # Gender-specific reference safety and context evaluation
        if ref_type == "gender_specific":
            if gender_to_use not in ("male", "female"):
                status = "Needs Review"
                bm["status"] = "Needs Review"
                bm["status_reason"] = "Gender-specific reference range requires patient gender context."
                bm["lower_limit"] = None
                bm["upper_limit"] = None
            else:
                st_res = calculate_status(val, ref_range, gender=gender_to_use)
                status = st_res.get("status", status)
                bm["status"] = status
                bm["status_reason"] = st_res.get("status_reason", bm.get("status_reason", ""))
                bm["lower_limit"] = st_res.get("lower_limit")
                bm["upper_limit"] = st_res.get("upper_limit")

        interp = interpret_biomarker(
            key=key,
            status=status,
            value=val,
            unit=unit,
            reference_range=ref_range,
        )

        enriched.append(
            {
                "key": key,
                "name": bm.get("name") or key.replace("_", " ").title(),
                "value": val,
                "unit": unit,
                "reference_range": ref_range,
                "reference_type": ref_type,
                "reference_source": ref_source,
                "status": status,
                "status_reason": bm.get("status_reason", ""),
                "lower_limit": bm.get("lower_limit"),
                "upper_limit": bm.get("upper_limit"),
                "interpretation": interp,
            }
        )
    return enriched


def _build_interpretation_engine_metadata() -> Dict[str, str]:
    return {"name": RULE_ENGINE_NAME, "version": RULE_ENGINE_VERSION}


# ──────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────

class SaveToVaultRequest(BaseModel):
    """
    The client supplies only the minimal identifiers needed to locate and
    re-derive the result.  The backend never persists client-supplied
    biomarker statuses, patterns, summaries, or reference ranges directly.
    """
    request_id: str
    filename: str
    report_type: str
    patient_gender: Optional[str] = None
    # Raw OCR / parsed report produced by SITA — biomarker values and
    # extracted references come from here, NOT client-computed statuses.
    raw_parsed_report: Dict[str, Any]
    # SHA-256 digest of the uploaded file supplied by the analyze endpoint
    # so the backend can detect duplicates without re-uploading.
    file_hash: str
    analyzed_at: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────

@router.post("/medical-reports/analyze")
async def analyze_medical_report(
    file: UploadFile = File(...),
    patient_gender: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/medical-reports/analyze

    End-to-end 100% deterministic medical lab report analysis pipeline:
    1.  Validates document format (PDF, PNG, JPG, JPEG) and file content
    2.  Computes SHA-256 hash for duplicate detection
    3.  Executes RapidOCR ONNX single-pass OCR
    4.  Identifies report type (CBC, LFT, KFT)
    5.  Extracts structured biomarkers and report-first reference ranges
    6.  Calculates biological bounds and status (with gender context protection)
    7.  Attaches deterministic educational explanations per biomarker
    8.  Runs cross-biomarker pattern detection
    9.  Generates deterministic narrative report summary
    10. Computes longitudinal trends against existing Health Vault records
    11. Returns rule-engine version metadata with every response

    Does NOT automatically persist to Health Vault until the user chooses to save.
    """
    import io

    t_start = time.perf_counter()
    request_id = uuid.uuid4().hex[:8]
    report_id = str(uuid.uuid4())

    if user_id is not None:
        from app.api.ocr import validate_uuid
        is_valid, err_msg = validate_uuid(user_id)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "user_id": user_id,
                    "report_id": None,
                    "error_code": "INVALID_USER_ID",
                    "message": err_msg or "A valid ABP User UUID is required.",
                },
            )

    # ── 1. File Format Validation ──────────────────────────────────────────
    filename_lower = (file.filename or "").lower()
    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]
    if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file format. Please upload a PDF, PNG, JPG, JPEG, or WEBP "
                "medical lab report."
            ),
        )

    # ── 2. Read file bytes, validate size / emptiness ─────────────────────
    try:
        raw_bytes = await file.read()
    except Exception:
        logger.error("[%s] Failed to read uploaded file bytes.", request_id)
        raise HTTPException(status_code=400, detail="Could not read the uploaded file.")

    if not raw_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty. Please upload a valid lab report.",
        )

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File exceeds the maximum allowed size of "
                f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            ),
        )

    # Basic content magic-byte check for image formats
    is_pdf = raw_bytes[:4] == b"%PDF"
    is_png = raw_bytes[:4] == b"\x89PNG"
    is_jpg = raw_bytes[:3] in (b"\xff\xd8\xff",)
    is_webp = raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP"
    ext = next((e for e in allowed_extensions if filename_lower.endswith(e)), "")
    if ext == ".pdf" and not is_pdf:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not appear to be a valid PDF.",
        )
    if ext == ".png" and not is_png:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not appear to be a valid PNG image.",
        )
    if ext in (".jpg", ".jpeg") and not is_jpg:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not appear to be a valid JPEG image.",
        )
    if ext == ".webp" and not is_webp:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not appear to be a valid WEBP image.",
        )

    # ── 3. SHA-256 Duplicate Check ─────────────────────────────────────────
    file_hash = _sha256_hex(raw_bytes)
    existing = get_report_by_hash(db, file_hash)
    if existing:
        saved_at_str = to_utc_iso(existing.saved_at or existing.created_at or existing.uploaded_at)
        analyzed_at_str = to_utc_iso(existing.analyzed_at or (existing.report_json or {}).get("analyzed_at")) or saved_at_str
        logger.info(
            "[%s] Duplicate report detected. Existing report_id=%s hash=%s...",
            request_id,
            existing.report_id,
            file_hash[:12],
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_report",
                "message": (
                    "This report has already been saved to your Health Vault. "
                    "Duplicate uploads are not permitted."
                ),
                "existing_report_id": existing.report_id,
                "saved_at": saved_at_str,
                "saved_to_vault_at": saved_at_str,
                "uploaded_at": saved_at_str,
                "analyzed_at": analyzed_at_str,
            },
        )

    # Re-wrap bytes as a seekable object for the OCR service
    file.file = io.BytesIO(raw_bytes)

    # ── 4. OCR Extraction ──────────────────────────────────────────────────
    t_ocr_start = time.perf_counter()
    try:
        ocr_result = await extract_text(file, request_id=request_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[%s] OCR extraction failed: %s", request_id, type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail=(
                "The document could not be processed by OCR. "
                "Please ensure the file is clear and readable."
            ),
        )
    t_ocr_ms = (time.perf_counter() - t_ocr_start) * 1000

    ocr_text = ocr_result.get("text", "")
    ocr_lines = ocr_result.get("ocr_lines", [])

    if not ocr_text.strip():
        logger.info("[%s] OCR returned empty text.", request_id)
        return {
            "request_id": request_id,
            "filename": file.filename,
            "status": "unreadable_report",
            "message": (
                "No text could be extracted from this document. "
                "Please upload a clear photo or digital PDF report."
            ),
            "is_supported": False,
            "report_type": "UNKNOWN",
            "biomarkers": [],
            "interpretation_engine": _build_interpretation_engine_metadata(),
        }

    # ── 5. Report Classification ───────────────────────────────────────────
    classification = classify_report(ocr_text)
    detected_type = classification.get("report_type", "UNKNOWN")

    if detected_type not in SUPPORTED_REPORT_TYPES:
        logger.info(
            "[%s] Unsupported report type: %s confidence=%.2f",
            request_id,
            detected_type,
            classification.get("confidence", 0.0),
        )
        return {
            "request_id": request_id,
            "filename": file.filename,
            "status": "unsupported_report_type",
            "is_supported": False,
            "report_type": detected_type,
            "confidence": classification.get("confidence", 0.0),
            "message": (
                f"Detected document type '{detected_type}' is not currently supported "
                "for automated analysis. Supported panels: Complete Blood Count (CBC), Liver Function (LFT), Kidney Function (KFT), and Lipid Profile."
            ),
            "supported_panels": [
                "Complete Blood Count (CBC)",
                "Liver Function Test (LFT)",
                "Kidney Function Test (KFT)",
                "Lipid Profile",
            ],
            "biomarkers": [],
            "interpretation_engine": _build_interpretation_engine_metadata(),
        }

    # ── 6. Deterministic Biomarker Parsing & Reference Resolution ─────────
    gender_to_use = (patient_gender or "unknown").strip().lower()
    try:
        parsed_report = route_report_parser(
            detected_type,
            ocr_text,
            ocr_lines=ocr_lines,
        )
    except Exception as exc:
        logger.error(
            "[%s] Parser failed for %s: %s", request_id, detected_type, type(exc).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "An internal error occurred while parsing the report. "
                "Please try again or contact support."
            ),
        )

    raw_biomarkers = parsed_report.get("biomarkers", [])

    if not raw_biomarkers:
        logger.warning(
            "[%s] Parser extracted 0 biomarkers for report_type=%s", request_id, detected_type
        )

    # Use report-extracted gender if explicit patient_gender is not provided
    report_patient_gender = (
        parsed_report.get("patient", {}).get("gender")
        or (parsed_report.get("metadata") or {}).get("patient", {}).get("gender")
    )
    if gender_to_use in ["", "unknown", None] and report_patient_gender:
        gender_to_use = report_patient_gender.strip().lower()

    # ── 6b. Pre-Rule Engine Biomarker Consistency Validation ───────────
    consistency_result = None
    if detected_type == "LIPID_PROFILE":
        from app.services.lipid_consistency_service import validate_lipid_consistency
        consistency_result = validate_lipid_consistency(raw_biomarkers)
        if not consistency_result["is_consistent"]:
            logger.warning(
                "[%s] Lipid internal consistency validation detected %d warning(s): %s",
                request_id,
                len(consistency_result["warnings"]),
                consistency_result["warnings"],
            )

    # ── 7. Server-Side Medical Rule Engine Enrichment ─────────────────────
    enriched_biomarkers = _enrich_biomarkers(raw_biomarkers, gender_to_use)

    # ── 8. Cross-Biomarker Pattern Detection ──────────────────────────────
    patterns = detect_cross_biomarker_patterns(enriched_biomarkers, report_type=detected_type)

    # ── 9. Report Summary ──────────────────────────────────────────────────
    summary = generate_deterministic_report_summary(
        parsed_report={"report_type": detected_type, "biomarkers": enriched_biomarkers},
        patterns=patterns,
    )
    health_summary = generate_health_summary(
        {"report_type": detected_type, "biomarkers": enriched_biomarkers}
    )

    # ── 10. Longitudinal Trends ────────────────────────────────────────────
    trends = compute_biomarker_trends(db, enriched_biomarkers, detected_type)

    # Extract distinct laboratory lifecycle dates
    raw_meta = parsed_report.get("metadata") or {}
    report_meta = parsed_report.get("report") or raw_meta.get("report") or {}
    patient_meta = parsed_report.get("patient") or raw_meta.get("patient") or {}
    report_date = (
        report_meta.get("report_date")
        or report_meta.get("collection_date")
        or report_meta.get("reported_date")
        or report_meta.get("received_date")
        or report_meta.get("ordered_date")
    )
    collection_date = report_meta.get("collection_date")
    reported_date = report_meta.get("reported_date")
    ordered_date = report_meta.get("ordered_date")
    received_date = report_meta.get("received_date")
    report_interpretation = (
        parsed_report.get("report_interpretation")
        or report_meta.get("report_interpretation")
        or raw_meta.get("report_interpretation")
    )
    analyzed_at_str = datetime.now(timezone.utc).isoformat()

    # ── 11. Zero-LLM Natural Language Explanation Layer ──────────────────
    explanation = generate_medical_explanation(
        report_type=detected_type,
        biomarkers=enriched_biomarkers,
        patterns=patterns,
        trends=trends,
        summary=summary,
        patient_gender=gender_to_use,
        report_date=report_date,
        report_interpretation=report_interpretation,
        consistency_result=consistency_result,
    )

    total_time_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # Attach user_id and report_id to each biomarker for microservice & Supabase integration
    for bm in enriched_biomarkers:
        bm["id"] = bm.get("id") or str(uuid.uuid4())
        bm["user_id"] = user_id
        bm["report_id"] = report_id
        bm["reference_min"] = bm.get("lower_limit")
        bm["reference_max"] = bm.get("upper_limit")
        bm["confidence"] = round(bm.get("confidence") or ocr_result.get("average_confidence", 1.0), 2)
        bm["created_at"] = analyzed_at_str

    report_record = {
        "id": report_id,
        "user_id": user_id,
        "report_type": detected_type,
        "report_date": report_date,
        "collection_date": collection_date,
        "reported_date": reported_date,
        "file_reference": file.filename,
        "ocr_status": "completed",
        "page_count": ocr_result.get("page_count", 1),
        "created_at": analyzed_at_str,
    }

    logger.info(
        "[%s] Analysis complete report_type=%s biomarkers=%d abnormal=%d "
        "ocr_ms=%.1f total_ms=%.1f",
        request_id,
        detected_type,
        len(enriched_biomarkers),
        summary.get("abnormal_total", 0),
        t_ocr_ms,
        total_time_ms,
    )

    import gc
    gc.collect()

    return {
        "success": True,
        "user_id": user_id,
        "report_id": report_id,
        "processing_status": "completed",
        "processing_time_ms": int(total_time_ms),
        "report": report_record,
        "request_id": request_id,
        "filename": file.filename,
        "file_hash": file_hash,
        "status": "success",
        "is_supported": True,
        "report_type": detected_type,
        "patient_gender": patient_gender or report_patient_gender or "not_specified",
        "patient": patient_meta,
        "report_date": report_date,
        "collection_date": collection_date,
        "reported_date": reported_date,
        "ordered_date": ordered_date,
        "received_date": received_date,
        "report_interpretation": report_interpretation,
        "analyzed_at": analyzed_at_str,
        "saved_at": None,
        "saved_to_vault_at": None,
        "summary": summary,
        "overall_status": health_summary.get("overall_status", "Healthy"),
        "patterns": patterns,
        "biomarkers": enriched_biomarkers,
        "trends": trends,
        "explanation": explanation,
        "consistency": consistency_result,
        "metadata": {
            "biomarkers_found": len(enriched_biomarkers),
            "abnormal_count": summary.get("abnormal_total", 0),
            "processing_time_ms": total_time_ms,
            "ocr_confidence": ocr_result.get("average_confidence", 1.0),
            "report_date": report_date,
            "collection_date": collection_date,
            "reported_date": reported_date,
            "report_interpretation": report_interpretation,
            "analyzed_at": analyzed_at_str,
            "saved_at": None,
            "saved_to_vault_at": None,
        },
        "interpretation_engine": _build_interpretation_engine_metadata(),
        "raw_parsed_report": parsed_report,
    }


@router.post("/medical-reports/save-to-health-vault")
def save_report_to_health_vault(
    payload: SaveToVaultRequest,
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/medical-reports/save-to-health-vault

    Explicit user action to persist an analyzed report to Health Vault.

    Security model:
    - The client supplies only the raw SITA parser output (biomarker values,
      extracted reference ranges) and identifying metadata.
    - The backend RE-RUNS the deterministic medical rule engine server-side to
      reconstruct all statuses, patterns, summaries, and educational explanations
      before persistence.  Client-computed interpretations are discarded.
    - Duplicate detection: SHA-256 file hash blocks re-saving identical reports.
    - Saved records include the rule engine version for future auditability.
    """
    # ── Duplicate Check ────────────────────────────────────────────────────
    existing = get_report_by_hash(db, payload.file_hash)
    if existing:
        saved_at_str = to_utc_iso(existing.saved_at or existing.created_at or existing.uploaded_at)
        analyzed_at_str = to_utc_iso(existing.analyzed_at or (existing.report_json or {}).get("analyzed_at")) or saved_at_str
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_report",
                "message": "This report has already been saved to your Health Vault.",
                "existing_report_id": existing.report_id,
                "saved_at": saved_at_str,
                "saved_to_vault_at": saved_at_str,
                "uploaded_at": saved_at_str,
                "analyzed_at": analyzed_at_str,
            },
        )

    # ── Validate raw_parsed_report ─────────────────────────────────────────
    raw_parsed = payload.raw_parsed_report
    if not raw_parsed or not raw_parsed.get("biomarkers"):
        raise HTTPException(
            status_code=400,
            detail="Invalid report payload: missing structured biomarker data.",
        )

    report_type = payload.report_type
    if report_type not in SUPPORTED_REPORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported report type '{report_type}'.",
        )

    # ── Server-Side Re-Interpretation (Backend Source of Truth) ───────────
    gender_to_use = (payload.patient_gender or "unknown").strip().lower()
    raw_biomarkers: List[Dict[str, Any]] = raw_parsed.get("biomarkers", [])
    enriched_biomarkers = _enrich_biomarkers(raw_biomarkers, gender_to_use)

    patterns = detect_cross_biomarker_patterns(enriched_biomarkers, report_type=report_type)
    summary = generate_deterministic_report_summary(
        parsed_report={"report_type": report_type, "biomarkers": enriched_biomarkers},
        patterns=patterns,
    )
    health_summary = generate_health_summary(
        {"report_type": report_type, "biomarkers": enriched_biomarkers}
    )

    overall_status = health_summary.get("overall_status", "Unknown")
    abnormal_count = summary.get("abnormal_total", 0)

    # Extract medical report dates from raw_parsed metadata
    raw_meta = raw_parsed.get("metadata") or {}
    report_meta = raw_meta.get("report") or {}
    report_date = (
        raw_parsed.get("report_date")
        or report_meta.get("report_date")
        or raw_meta.get("report_date")
        or raw_meta.get("collection_date")
    )
    collection_date = (
        raw_parsed.get("collection_date")
        or report_meta.get("collection_date")
        or raw_meta.get("collection_date")
    )
    reported_date = (
        raw_parsed.get("reported_date")
        or report_meta.get("reported_date")
        or raw_meta.get("reported_date")
    )
    report_interpretation = (
        raw_parsed.get("report_interpretation")
        or report_meta.get("report_interpretation")
        or raw_meta.get("report_interpretation")
    )

    consistency_result = raw_parsed.get("consistency")
    if consistency_result is None and report_type == "LIPID_PROFILE":
        from app.services.lipid_consistency_service import validate_lipid_consistency
        consistency_result = validate_lipid_consistency(raw_biomarkers)

    explanation = generate_medical_explanation(
        report_type=report_type,
        biomarkers=enriched_biomarkers,
        patterns=patterns,
        summary=summary,
        patient_gender=payload.patient_gender,
        report_date=report_date,
        report_interpretation=report_interpretation,
        consistency_result=consistency_result,
    )

    # Exact authoritative timestamps
    saved_now_dt = datetime.now(timezone.utc)
    saved_at_str = saved_now_dt.isoformat()
    analyzed_at_val = to_utc_iso(
        payload.analyzed_at
        or raw_parsed.get("analyzed_at")
        or raw_meta.get("analyzed_at")
    ) or saved_at_str

    # ── Build Vault Payload ────────────────────────────────────────────────
    vault_payload = {
        "report_id": payload.request_id,
        "filename": payload.filename,
        "report_type": report_type,
        "report_date": report_date,
        "collection_date": collection_date,
        "reported_date": reported_date,
        "report_interpretation": report_interpretation,
        "analyzed_at": analyzed_at_val,
        "saved_at": saved_at_str,
        "saved_to_vault_at": saved_at_str,
        "uploaded_at": saved_at_str,
        "overall_status": overall_status,
        "abnormal_count": abnormal_count,
        "file_hash": payload.file_hash,
        "interpretation_engine_version": RULE_ENGINE_VERSION,
        "classification": {"report_type": report_type},
        "parsed_report": raw_parsed,
        "explanation": explanation,
        "consistency": consistency_result,
        "metadata": {
            "report_date": report_date,
            "collection_date": collection_date,
            "reported_date": reported_date,
            "analyzed_at": analyzed_at_val,
            "saved_at": saved_at_str,
            "saved_to_vault_at": saved_at_str,
            "report": report_meta,
        },
        "health_summary": {
            "overall_status": overall_status,
            "abnormal_count": abnormal_count,
            "summary": summary,
        },
        "analysis": {
            "biomarkers": enriched_biomarkers,
            "patterns": patterns,
            "summary": summary,
            "explanation": explanation,
            "interpretation_engine": _build_interpretation_engine_metadata(),
        },
    }

    try:
        saved_record = create_report(db, vault_payload)
    except Exception as exc:
        logger.exception(
            "Health Vault save failed for request_id=%s report_type=%s: %s",
            payload.request_id,
            report_type,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to save report to Health Vault. Please try again.",
        )

    logger.info(
        "Health Vault save OK report_id=%s report_type=%s overall_status=%s "
        "abnormal=%d engine_version=%s",
        saved_record.report_id,
        report_type,
        overall_status,
        abnormal_count,
        RULE_ENGINE_VERSION,
    )

    authoritative_saved_at = to_utc_iso(saved_record.saved_at or saved_record.created_at) or saved_at_str
    return {
        "saved": True,
        "report_id": saved_record.report_id,
        "report_date": report_date,
        "analyzed_at": analyzed_at_val,
        "saved_at": authoritative_saved_at,
        "saved_to_vault_at": authoritative_saved_at,
        "uploaded_at": authoritative_saved_at,
        "overall_status": overall_status,
        "abnormal_count": abnormal_count,
        "interpretation_engine": _build_interpretation_engine_metadata(),
        "message": "Report successfully saved to your Health Vault.",
    }


@router.get("/medical-reports/{report_id}")
def get_medical_report_analysis(
    report_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/medical-reports/{report_id}
    Retrieves a stored medical report and its analysis metadata from Health Vault.
    """
    record = get_report(db, report_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Medical report '{report_id}' was not found in Health Vault.",
        )

    saved_at_str = to_utc_iso(record.saved_at or record.created_at or record.uploaded_at)
    r_json = record.report_json or {}
    report_date = (
        r_json.get("report_date")
        or (r_json.get("metadata") or {}).get("report_date")
        or (r_json.get("metadata") or {}).get("report", {}).get("report_date")
    )
    analyzed_at_raw = (
        r_json.get("analyzed_at")
        or (r_json.get("metadata") or {}).get("analyzed_at")
    )
    analyzed_at_str = to_utc_iso(analyzed_at_raw) if analyzed_at_raw else saved_at_str

    report_interpretation = (
        r_json.get("report_interpretation")
        or (r_json.get("metadata") or {}).get("report_interpretation")
        or (r_json.get("parsed_report") or {}).get("report_interpretation")
    )

    return {
        "report_id": record.report_id,
        "filename": record.filename,
        "report_type": record.report_type,
        "report_date": report_date,
        "report_interpretation": report_interpretation,
        "analyzed_at": analyzed_at_str,
        "saved_at": saved_at_str,
        "saved_to_vault_at": saved_at_str,
        "overall_status": record.overall_status,
        "uploaded_at": saved_at_str,
        "interpretation_engine_version": record.interpretation_engine_version,
        "report_data": record.report_json,
    }
