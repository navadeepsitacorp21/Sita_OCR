import time
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.ocr_service import extract_text
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights
from app.database import get_db, create_report

logger = logging.getLogger("sita.ocr")
router = APIRouter(tags=["Upload"])


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    t_req_start = time.perf_counter()
    request_id = uuid.uuid4().hex[:8]

    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg"]

    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, PNG, JPG, and JPEG files are supported."
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
    print(f"\n[UPLOAD_DEBUG] report_type={classification['report_type']} parser_version={parsed_report.get('parser_version')} biomarkers_count={len(parsed_report.get('biomarkers', []))}")

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
        uploaded_at_str = (
            saved_record.uploaded_at.isoformat()
            if hasattr(saved_record.uploaded_at, "isoformat")
            else str(saved_record.uploaded_at)
        )
        health_vault_info = {
            "report_id": saved_record.report_id,
            "uploaded_at": uploaded_at_str,
            "saved": True
        }
    except Exception:
        health_vault_info = {
            "saved": False,
            "error": "database_save_failed"
        }
    t_db_ms = (time.perf_counter() - t_db_start) * 1000

    total_req_ms = (time.perf_counter() - t_req_start) * 1000

    # Structured Performance Logging (Production-safe, zero PII)
    print(
        f"\nSITA OCR PERFORMANCE\n"
        f"request_id={request_id}\n"
        f"provider={perf_meta.get('provider', 'rapidocr')}\n"
        f"page={result.get('page_count', 1)}/{result.get('page_count', 1)}\n"
        f"image={result.get('image_dims', 'N/A')}\n"
        f"ocr_invocations={perf_meta.get('ocr_calls', 1)}\n"
        f"preprocessing_ms={perf_meta.get('preprocess_ms', 0.0):.1f}\n"
        f"ocr_inference_ms={perf_meta.get('ocr_inference_ms', 0.0):.1f}\n"
        f"postprocessing_ms={perf_meta.get('ocr_total_ms', 0.0) - perf_meta.get('ocr_inference_ms', 0.0) - perf_meta.get('preprocess_ms', 0.0):.1f}\n"
        f"parsing_ms={t_parse_ms:.1f}\n"
        f"validation_ms={t_val_ms:.1f}\n"
        f"database_ms={t_db_ms:.1f}\n"
        f"total_ms={total_req_ms:.1f}\n"
        f"ocr_lines={perf_meta.get('ocr_lines_count', len(ocr_lines))}\n"
        f"avg_confidence={perf_meta.get('avg_confidence', 0.0):.2f}"
    )

    return {
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