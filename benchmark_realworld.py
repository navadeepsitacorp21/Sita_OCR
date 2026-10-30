import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend"))

from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary

def run_realworld_validation():
    print("=" * 70)
    print("SITA OCR REAL-WORLD IMAGE QUALITY VALIDATION MATRIX")
    print("=" * 70)

    variations = [
        ("A. Clean Report", "benchmark_data/realworld/A_clean_report.png"),
        ("B. Phone Photograph (Skew/Distort)", "benchmark_data/realworld/B_phone_photograph.png"),
        ("C. Low-Light Photograph", "benchmark_data/realworld/C_low_light.png"),
        ("D. Slightly Blurry Image", "benchmark_data/realworld/D_blurry.png"),
        ("E. Rotated Report (8 deg)", "benchmark_data/realworld/E_rotated_8deg.png"),
        ("F. Shadowed Report", "benchmark_data/realworld/F_shadowed.png"),
        ("G. Compressed Image (JPEG)", "benchmark_data/realworld/G_compressed.jpg"),
        ("H. Small Text / Distance", "benchmark_data/realworld/H_small_text.png"),
    ]

    provider = get_ocr_provider()

    for name, path in variations:
        t0 = time.perf_counter()
        lines = provider.extract_from_image(path)
        t_ocr = time.perf_counter() - t0

        line_count = len(lines)
        avg_conf = sum(l.get("confidence", 0) for l in lines) / line_count if line_count else 0.0

        ocr_text = "\n".join([l["text"] for l in lines])
        clf = classify_report(ocr_text)
        parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=lines)
        summary = generate_health_summary(parsed)

        found = parsed.get("biomarkers_found", 0)
        missing = parsed.get("biomarkers_missing", [])

        print(f"\n[{name}]")
        print(f"  OCR Time: {t_ocr*1000:.1f} ms ({t_ocr:.2f} s)")
        print(f"  Detected Text Lines: {line_count}")
        print(f"  Average Confidence: {avg_conf:.3f}")
        print(f"  Report Classification: {clf.get('report_type')} ({clf.get('confidence', 0):.2f})")
        print(f"  Biomarkers Found: {found}")
        print(f"  Health Summary: Overall '{summary.get('overall_status')}', Abnormals: {summary.get('abnormal_count', 0)}")
        if found > 0:
            bm_names = [b["key"] for b in parsed.get("biomarkers", [])]
            print(f"  Extracted Biomarkers: {', '.join(bm_names)}")

if __name__ == "__main__":
    run_realworld_validation()
