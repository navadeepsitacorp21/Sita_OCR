import time
import os
import sys
import json

sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal, create_report
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights
from app.services.ocr_service import _extract_lines_and_confidence_from_ocr_res

def run_benchmark():
    output_lines = []
    output_lines.append("=== SITA OCR ENGINE PERFORMANCE PROFILING ===")

    # 1. OCR Model Initialization
    t0 = time.perf_counter()
    from paddleocr import PaddleOCR
    t_import = time.perf_counter() - t0

    t0 = time.perf_counter()
    ocr = PaddleOCR(lang="en", enable_mkldnn=False, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
    t_init = time.perf_counter() - t0

    output_lines.append(f"PaddleOCR Import time: {t_import*1000:.2f}ms")
    output_lines.append(f"PaddleOCR Model Initialization time: {t_init*1000:.2f}ms")

    reports = [
        ("Aster CBC", "benchmark_data/aster_cbc.png"),
        ("Labsmart CBC", "benchmark_data/labsmart_cbc.png"),
        ("Care Diagnostics LFT", "benchmark_data/lft_complete.png")
    ]

    all_results = {}

    for name, path in reports:
        output_lines.append("\n" + "="*50)
        output_lines.append(f"PROFILING REPORT: {name} ({path})")
        output_lines.append("="*50)

        runs = []
        for run_idx in range(4): # run 0 = cold inference, run 1,2,3 = warm
            t0 = time.perf_counter()
            with open(path, "rb") as f:
                content = f.read()
            t_file_read = time.perf_counter() - t0

            import cv2
            t0 = time.perf_counter()
            img = cv2.imread(path)
            h, w = img.shape[:2]
            t_img_load = time.perf_counter() - t0

            t0 = time.perf_counter()
            max_dim = max(h, w)
            if max_dim > 1280:
                scale = 1280.0 / max_dim
                img_proc = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            else:
                img_proc = img
            t_preprocess = time.perf_counter() - t0

            t0 = time.perf_counter()
            ocr_res = ocr.ocr(path)
            t_ocr_infer = time.perf_counter() - t0

            t0 = time.perf_counter()
            ocr_lines = _extract_lines_and_confidence_from_ocr_res(ocr_res)
            ocr_text = "\n".join([line["text"] for line in ocr_lines])
            t_text_extract = time.perf_counter() - t0

            t0 = time.perf_counter()
            classification = classify_report(ocr_text)
            t_classify = time.perf_counter() - t0

            t0 = time.perf_counter()
            parsed_report = route_report_parser(
                classification["report_type"],
                ocr_text,
                ocr_lines=ocr_lines
            )
            t_parse = time.perf_counter() - t0

            t0 = time.perf_counter()
            health_summary = generate_health_summary(parsed_report)
            health_highlights = generate_health_highlights(parsed_report)
            t_summary = time.perf_counter() - t0

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

            total_time = t_file_read + t_img_load + t_preprocess + t_ocr_infer + t_text_extract + t_classify + t_parse + t_summary + t_db
            run_data = {
                "run": "Cold" if run_idx == 0 else f"Warm {run_idx}",
                "file_read_ms": round(t_file_read * 1000, 2),
                "img_load_ms": round(t_img_load * 1000, 2),
                "preprocess_ms": round(t_preprocess * 1000, 2),
                "ocr_infer_s": round(t_ocr_infer, 3),
                "text_extract_ms": round(t_text_extract * 1000, 2),
                "classify_ms": round(t_classify * 1000, 2),
                "parse_ms": round(t_parse * 1000, 2),
                "summary_ms": round(t_summary * 1000, 2),
                "db_ms": round(t_db * 1000, 2),
                "total_s": round(total_time, 3),
                "biomarkers": parsed_report.get("biomarkers_found", 0)
            }
            runs.append(run_data)
            output_lines.append(f"[{run_data['run']}] Total: {run_data['total_s']}s | OCR: {run_data['ocr_infer_s']}s | Parse: {run_data['parse_ms']}ms | DB: {run_data['db_ms']}ms | Biomarkers: {run_data['biomarkers']}")

        all_results[name] = runs

    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    with open("benchmark_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print("Benchmark complete. Written to benchmark_results.json and benchmark_summary.txt")

if __name__ == "__main__":
    run_benchmark()
