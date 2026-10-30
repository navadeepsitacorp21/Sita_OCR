import time
import os
import sys
import json
import statistics

sys.path.insert(0, os.path.abspath("backend"))

from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights

def run_benchmarks():
    reports = [
        ("Aster CBC", "benchmark_data/aster_cbc.png"),
        ("Labsmart CBC", "benchmark_data/labsmart_cbc.png"),
        ("Care Diagnostics LFT", "benchmark_data/lft_complete.png")
    ]

    print("=" * 60)
    print("SITA OCR BENCHMARK: RapidOCR ONNX Runtime vs PaddleOCR Baseline")
    print("=" * 60)

    # 1. Warm up RapidOCR singleton
    t0 = time.perf_counter()
    rapid_provider = get_ocr_provider()
    t_rapid_init = (time.perf_counter() - t0) * 1000
    print(f"RapidOCR Provider Init Time: {t_rapid_init:.2f} ms")

    # Warmup inference
    rapid_provider.extract_from_image(reports[0][1])

    results = {}

    for name, path in reports:
        print(f"\nEvaluating: {name} ({path})")
        ocr_times = []
        parse_times = []
        total_times = []
        biomarker_counts = []

        for run in range(3):
            t0 = time.perf_counter()
            lines = rapid_provider.extract_from_image(path)
            t_ocr = time.perf_counter() - t0

            t0 = time.perf_counter()
            ocr_text = "\n".join([l["text"] for l in lines])
            clf = classify_report(ocr_text)
            parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=lines)
            t_parse = time.perf_counter() - t0

            t_total = t_ocr + t_parse
            ocr_times.append(t_ocr)
            parse_times.append(t_parse)
            total_times.append(t_total)
            biomarker_counts.append(parsed.get("biomarkers_found", 0))

            print(f"  Run {run+1}: OCR={t_ocr*1000:.1f}ms, Parse={t_parse*1000:.1f}ms, Total={t_total:.3f}s, Biomarkers={parsed.get('biomarkers_found')}")

        results[name] = {
            "runs_ocr_s": [round(t, 3) for t in ocr_times],
            "avg_ocr_s": round(statistics.mean(ocr_times), 3),
            "min_ocr_s": round(min(ocr_times), 3),
            "max_ocr_s": round(max(ocr_times), 3),
            "avg_parse_ms": round(statistics.mean(parse_times) * 1000, 1),
            "avg_total_s": round(statistics.mean(total_times), 3),
            "biomarkers": biomarker_counts[-1]
        }

    print("\n" + "=" * 60)
    print("SUMMARY RESULTS (RapidOCR ONNX)")
    print("=" * 60)
    for name, res in results.items():
        print(f"{name}:")
        print(f"  OCR (Runs 1-3): {res['runs_ocr_s']} s")
        print(f"  OCR Avg: {res['avg_ocr_s']}s (Min: {res['min_ocr_s']}s, Max: {res['max_ocr_s']}s)")
        print(f"  Parse Avg: {res['avg_parse_ms']} ms")
        print(f"  Total Request Avg: {res['avg_total_s']} s")
        print(f"  Biomarkers Extracted: {res['biomarkers']}")

if __name__ == "__main__":
    run_benchmarks()
