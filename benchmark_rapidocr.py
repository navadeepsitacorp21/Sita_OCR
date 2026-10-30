import time
import os
import sys
# pyrefly: ignore[missing-import]
from rapidocr_onnxruntime import RapidOCR

sys.path.insert(0, os.path.abspath("backend"))
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.database import SessionLocal, create_report
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights

engine = RapidOCR()

reports = [
    ("Aster CBC", "benchmark_data/aster_cbc.png"),
    ("Labsmart CBC", "benchmark_data/labsmart_cbc.png"),
    ("Care Diagnostics LFT", "benchmark_data/lft_complete.png")
]

for name, path in reports:
    print(f"\n--- Benchmarking RapidOCR ONNX on {name} ---")
    for r in range(3):
        t0 = time.perf_counter()
        res, elapse = engine(path)
        t_ocr = time.perf_counter() - t0

        ocr_lines = []
        if res:
            for item in res:
                # item: [box, text, score]
                ocr_lines.append({
                    "text": item[1],
                    "confidence": float(item[2])
                })
        ocr_text = "\n".join([l["text"] for l in ocr_lines])

        t0 = time.perf_counter()
        clf = classify_report(ocr_text)
        parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=ocr_lines)
        t_parse = time.perf_counter() - t0

        print(f"Run {r+1}: OCR={t_ocr:.3f}s, Parse={t_parse*1000:.1f}ms, Biomarkers found={parsed.get('biomarkers_found', 0)}")
