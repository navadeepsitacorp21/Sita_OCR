import time
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal, create_report
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights

def profile_stages():
    print("=== SITA OCR ENGINE PERFORMANCE PROFILING ===")

    # 1. OCR Model Initialization
    t0 = time.perf_counter()
    from paddleocr import PaddleOCR
    t_import = time.perf_counter() - t0

    t0 = time.perf_counter()
    ocr = PaddleOCR(lang="en", enable_mkldnn=False, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
    t_init = time.perf_counter() - t0

    print(f"PaddleOCR Import time: {t_import*1000:.2f}ms")
    print(f"PaddleOCR Model Initialization time: {t_init*1000:.2f}ms")

    # Benchmarks
    reports = [
        ("Aster CBC", "benchmark_data/aster_cbc.png"),
        ("Labsmart CBC", "benchmark_data/labsmart_cbc.png"),
        ("Care Diagnostics LFT", "benchmark_data/lft_complete.png")
    ]

    for name, path in reports:
        print(f"\n==========================================")
        print(f"PROFILING REPORT: {name} ({path})")
        print(f"==========================================")

        # File read & image dimensions
        t0 = time.perf_counter()
        with open(path, "rb") as f:
            content = f.read()
        t_file_read = time.perf_counter() - t0

        import cv2
        t0 = time.perf_counter()
        img = cv2.imread(path)
        h, w = img.shape[:2]
        t_img_load = time.perf_counter() - t0
        print(f"Original dimensions: {w}x{h}, File size: {len(content)} bytes")

        # Preprocessing (downscaling if needed)
        t0 = time.perf_counter()
        max_dim = max(h, w)
        if max_dim > 1280:
            scale = 1280.0 / max_dim
            img_processed = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        else:
            img_processed = img
        t_preprocess = time.perf_counter() - t0
        print(f"Processed dimensions: {img_processed.shape[1]}x{img_processed.shape[0]}")

        # OCR Inference
        t0 = time.perf_counter()
        ocr_res = ocr.ocr(path)
        t_ocr_infer = time.perf_counter() - t0

        # Text extraction
        t0 = time.perf_counter()
        from app.services.ocr_service import _extract_lines_and_confidence_from_ocr_res
        ocr_lines = _extract_lines_and_confidence_from_ocr_res(ocr_res)
        ocr_text = "\n".join([line["text"] for line in ocr_lines])
        t_text_extract = time.perf_counter() - t0

        # Classification / Report detection
        t0 = time.perf_counter()
        classification = classify_report(ocr_text)
        t_classify = time.perf_counter() - t0

        # Biomarker parsing + Reference parsing + Number/Unit normalization
        t0 = time.perf_counter()
        parsed_report = route_report_parser(
            classification["report_type"],
            ocr_text,
            ocr_lines=ocr_lines
        )
        t_parse = time.perf_counter() - t0

        # Health summary & highlights
        t0 = time.perf_counter()
        health_summary = generate_health_summary(parsed_report)
        health_highlights = generate_health_highlights(parsed_report)
        t_summary = time.perf_counter() - t0

        # Database operations
        t0 = time.perf_counter()
        db = SessionLocal()
        report_payload = {
            "filename": os.path.basename(path),
            "page_count": 1,
            "ocr_summary": {"average_confidence": 0.95},
            "classification": classification,
            "parsed_report": parsed_report,
            "health_summary": health_summary,
            "health_highlights": health_highlights
        }
        saved_record = create_report(db, report_payload)
        db.close()
        t_db = time.perf_counter() - t0

        total_req = t_file_read + t_img_load + t_preprocess + t_ocr_infer + t_text_extract + t_classify + t_parse + t_summary + t_db

        print("\nSITA OCR PERFORMANCE BREAKDOWN")
        print("────────────────────────────────────────────")
        print(f"File read                 {t_file_read*1000:8.2f} ms")
        print(f"Image load                {t_img_load*1000:8.2f} ms")
        print(f"Image preprocessing       {t_preprocess*1000:8.2f} ms")
        print(f"OCR inference             {t_ocr_infer:8.2f} s  ({t_ocr_infer/total_req*100:.1f}%)")
        print(f"Text extraction           {t_text_extract*1000:8.2f} ms")
        print(f"Report detection          {t_classify*1000:8.2f} ms")
        print(f"Biomarker & Ref Parsing   {t_parse*1000:8.2f} ms")
        print(f"Health summary & alerts   {t_summary*1000:8.2f} ms")
        print(f"Database save             {t_db*1000:8.2f} ms")
        print("────────────────────────────────────────────")
        print(f"TOTAL REQUEST TIME        {total_req:8.2f} s")
        print(f"Biomarkers parsed: {parsed_report.get('biomarkers_found', 0)}")

if __name__ == "__main__":
    profile_stages()
