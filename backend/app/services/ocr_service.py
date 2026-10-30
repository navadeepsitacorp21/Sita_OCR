import asyncio
import os
import tempfile
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException
import pymupdf  # PyMuPDF
import cv2
import numpy as np
from app.services.ocr import get_ocr_provider, extract_with_provider_resilience, OCRError, OCRTimeoutError

logger = logging.getLogger("sita.ocr")


def _extract_lines_and_confidence_from_ocr_res(result) -> List[Dict[str, Any]]:
    """
    Backward-compatibility helper for any legacy tests referencing this function directly.
    """
    if not result:
        return []
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "text" in result[0]:
        return result
    provider = get_ocr_provider()
    return provider.extract_from_image(result) if hasattr(provider, "extract_from_image") else []


async def extract_text(file: UploadFile, request_id: Optional[str] = None) -> dict:
    """
    Extract text and OCR confidence scores from PDF or image using RapidOCR ONNX backend.
    1. For native digital PDFs, extracts high-fidelity text instantly via PyMuPDF (~10-50ms).
    2. For scanned PDFs/images, runs RapidOCR ONNX (with 1 OCR call per page).
    Returns page count, full extracted text, average_confidence, detailed ocr_lines (with bbox & confidence),
    and structured performance metrics.
    """
    t_start = time.perf_counter()
    req_id = request_id or uuid.uuid4().hex[:8]
    provider = get_ocr_provider()
    provider_name = "rapidocr" if "rapid" in provider.__class__.__name__.lower() else "paddleocr"

    suffix = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    t_read_done = time.perf_counter()
    file_read_ms = (t_read_done - t_start) * 1000

    extracted_pages: List[str] = []
    all_ocr_lines: List[Dict[str, Any]] = []
    ocr_calls = 0
    t_preprocess_total_ms = 0.0
    t_inference_total_ms = 0.0
    image_dims = "N/A"
    is_digital_fastpath = False

    try:
        # -------- PDF --------
        if suffix == ".pdf":
            pdf = await asyncio.to_thread(pymupdf.open, temp_path)
            num_pages = len(pdf)

            digital_pages_text = []
            total_chars = 0

            for page in pdf:
                p_text = page.get_text().strip()
                digital_pages_text.append(p_text)
                total_chars += len(p_text)

            # Native digital PDF fast-path (>= 50 chars per report average)
            if total_chars >= 50:
                is_digital_fastpath = True
                for page_num, p_text in enumerate(digital_pages_text, 1):
                    lines = [l.strip() for l in p_text.split("\n") if l.strip()]
                    for l in lines:
                        all_ocr_lines.append({
                            "text": l,
                            "confidence": 1.0,
                            "bbox": []
                        })
                    extracted_pages.append("\n".join(lines))
            else:
                # Scanned image PDF: render each page sequentially and run RapidOCR
                for page_idx, page in enumerate(pdf):
                    page_num = page_idx + 1
                    t_pre0 = time.perf_counter()
                    pix = await asyncio.to_thread(page.get_pixmap, dpi=120)
                    image_path = temp_path + f"_page_{page_num}.png"
                    await asyncio.to_thread(pix.save, image_path)

                    try:
                        img = cv2.imread(image_path)
                        if img is not None:
                            h, w = img.shape[:2]
                            image_dims = f"{w}x{h}"
                            max_dim = max(h, w)
                            if max_dim > 2048:
                                scale = 2048.0 / max_dim
                                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                                cv2.imwrite(image_path, img)
                                image_dims = f"{img.shape[1]}x{img.shape[0]}"
                        t_preprocess_total_ms += (time.perf_counter() - t_pre0) * 1000

                        t_inf0 = time.perf_counter()
                        try:
                            lines = await asyncio.to_thread(extract_with_provider_resilience, image_path, provider)
                        except OCRTimeoutError as te:
                            logger.error(f"[{req_id}] Page {page_num}/{num_pages} OCR timeout: {te}")
                            raise HTTPException(status_code=504, detail=f"OCR timeout processing page {page_num}: {te}")
                        except OCRError as oe:
                            logger.error(f"[{req_id}] Page {page_num}/{num_pages} OCR error: {oe}")
                            raise HTTPException(status_code=500, detail=f"OCR error processing page {page_num}: {oe}")

                        t_inference_total_ms += (time.perf_counter() - t_inf0) * 1000
                        ocr_calls += 1

                        all_ocr_lines.extend(lines)
                        page_text = [item["text"] for item in lines]
                        extracted_pages.append("\n".join(page_text))
                    finally:
                        if os.path.exists(image_path):
                            os.remove(image_path)

            pdf.close()

        # -------- IMAGE --------
        else:
            t_pre0 = time.perf_counter()
            img = None
            try:
                img = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
            except Exception:
                img = None
            if img is None:
                img = cv2.imread(temp_path)

            if img is not None:
                h, w = img.shape[:2]
                image_dims = f"{w}x{h}"
                max_dim = max(h, w)
                if max_dim > 1500:
                    scale = 1500.0 / max_dim
                    img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                    cv2.imwrite(temp_path, img)
                    image_dims = f"{img.shape[1]}x{img.shape[0]}"
                del img
            t_preprocess_total_ms += (time.perf_counter() - t_pre0) * 1000

            t_inf0 = time.perf_counter()
            try:
                lines = await asyncio.to_thread(extract_with_provider_resilience, temp_path, provider)
            except OCRTimeoutError as te:
                logger.error(f"[{req_id}] Image OCR timeout: {te}")
                raise HTTPException(status_code=504, detail=f"OCR timeout: {te}")
            except OCRError as oe:
                logger.error(f"[{req_id}] Image OCR error: {oe}")
                raise HTTPException(status_code=500, detail=f"OCR error: {oe}")

            t_inference_total_ms += (time.perf_counter() - t_inf0) * 1000
            ocr_calls += 1

            all_ocr_lines.extend(lines)
            page_text = [item["text"] for item in lines]
            extracted_pages.append("\n".join(page_text))

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    avg_confidence = (
        round(sum(line["confidence"] for line in all_ocr_lines) / len(all_ocr_lines), 3)
        if all_ocr_lines else 0.0
    )

    t_total_ms = (time.perf_counter() - t_start) * 1000
    page_count = len(extracted_pages) if extracted_pages else 1

    return {
        "request_id": req_id,
        "page_count": page_count,
        "text": "\n\n".join(extracted_pages),
        "average_confidence": avg_confidence,
        "ocr_lines": all_ocr_lines,
        "is_digital_fastpath": is_digital_fastpath,
        "image_dims": image_dims,
        "performance": {
            "request_id": req_id,
            "provider": provider_name,
            "page_count": page_count,
            "image_dims": image_dims,
            "ocr_calls": ocr_calls,
            "file_read_ms": round(file_read_ms, 2),
            "preprocess_ms": round(t_preprocess_total_ms, 2),
            "ocr_inference_ms": round(t_inference_total_ms, 2),
            "ocr_total_ms": round(t_total_ms, 2),
            "ocr_lines_count": len(all_ocr_lines),
            "avg_confidence": avg_confidence
        }
    }