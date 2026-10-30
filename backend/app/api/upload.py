import time
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.ocr_service import extract_text
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights
from app.database import get_db, create_report
from app.database.models import to_utc_iso

logger = logging.getLogger("sita.ocr")
router = APIRouter(tags=["Upload"])


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    t_req_start = time.perf_counter()
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

    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]

    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, PNG, JPG, JPEG, and WEBP files are supported."
        )

    # 1. OCR Extraction (with PyMuPDF fast-path or RapidOCR ONNX)
    result = await extract_text(file, request_id=request_id)
    ocr_text = result["text"]
    ocr_lines = result.get("ocr_lines", [])
    perf_meta = result.get("performance", {})

    # 2. Classification & Parsing
    t_parse_start = time.perf_counter()
    classification = classify_report(ocr_text)
    parsed_report = route_report_parser(
        classification["report_type"],
        ocr_text,
        ocr_lines=ocr_lines
    )
    t_parse_ms = (time.perf_counter() - t_parse_start) * 1000
    logger.debug(
        "[%s] report_type=%s parser_version=%s biomarkers_count=%d",
        request_id,
        classification["report_type"],
        parsed_report.get("parser_version"),
        len(parsed_report.get("biomarkers", [])),
    )

    # 3. Validation & Health Summary
    t_val_start = time.perf_counter()
    health_summary = generate_health_summary(parsed_report)
    health_highlights = generate_health_highlights(parsed_report)
    t_val_ms = (time.perf_counter() - t_val_start) * 1000

    report_payload = {
        "filename": file.filename,
        "page_count": result.get("page_count", 1),
        "ocr_summary": {
            "average_confidence": result.get("average_confidence", 0.0)
        },
        "classification": classification,
        "parsed_report": parsed_report,
        "health_summary": health_summary,
        "health_highlights": health_highlights
    }

    # 4. Database Save
    t_db_start = time.perf_counter()
    try:
        saved_record = create_report(db, report_payload)
        saved_at_str = to_utc_iso(saved_record.saved_at or saved_record.created_at)
        health_vault_info = {
            "report_id": saved_record.report_id,
            "uploaded_at": saved_at_str,
            "saved_at": saved_at_str,
            "saved": True
        }
    except Exception:
        health_vault_info = {
            "saved": False,
            "error": "database_save_failed"
        }
    t_db_ms = (time.perf_counter() - t_db_start) * 1000

    total_req_ms = (time.perf_counter() - t_req_start) * 1000

    logger.info(
        "[%s] provider=%s pages=%d/%d image=%s ocr_calls=%d "
        "preprocess_ms=%.1f ocr_inference_ms=%.1f postprocess_ms=%.1f "
        "parsing_ms=%.1f validation_ms=%.1f database_ms=%.1f total_ms=%.1f "
        "ocr_lines=%d avg_confidence=%.2f",
        request_id,
        perf_meta.get("provider", "rapidocr"),
        result.get("page_count", 1),
        result.get("page_count", 1),
        result.get("image_dims", "N/A"),
        perf_meta.get("ocr_calls", 1),
        perf_meta.get("preprocess_ms", 0.0),
        perf_meta.get("ocr_inference_ms", 0.0),
        perf_meta.get("ocr_total_ms", 0.0) - perf_meta.get("ocr_inference_ms", 0.0) - perf_meta.get("preprocess_ms", 0.0),
        t_parse_ms,
        t_val_ms,
        t_db_ms,
        total_req_ms,
        perf_meta.get("ocr_lines_count", len(ocr_lines)),
        perf_meta.get("avg_confidence", 0.0),
    )

    return {
        "user_id": user_id,
        "report_id": report_id,
        "request_id": request_id,
        "filename": file.filename,
        "status": "processed",
        "page_count": result["page_count"],
        "ocr_summary": {
            "average_confidence": result.get("average_confidence", 0.0)
        },
        "classification": classification,
        "parsed_report": parsed_report,
        "health_summary": health_summary,
        "health_highlights": health_highlights,
        "health_vault": health_vault_info,
        "performance": {
            "request_id": request_id,
            "provider": perf_meta.get("provider", "rapidocr"),
            "ocr_calls": perf_meta.get("ocr_calls", 1),
            "preprocess_ms": perf_meta.get("preprocess_ms", 0.0),
            "ocr_inference_ms": perf_meta.get("ocr_inference_ms", 0.0),
            "parsing_ms": round(t_parse_ms, 2),
            "validation_ms": round(t_val_ms, 2),
            "database_ms": round(t_db_ms, 2),
            "total_ms": round(total_req_ms, 2)
        }
    }