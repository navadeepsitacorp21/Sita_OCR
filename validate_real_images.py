import sys
import os
import time

sys.path.insert(0, os.path.abspath("backend"))

from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary


def test_image(img_path, expected_type=None):
    print("=" * 80)
    print(f"RUNNING IMAGE PIPELINE: {img_path}")
    print("=" * 80)

    if not os.path.exists(img_path):
        print(f"ERROR: Image not found: {img_path}")
        return

    ocr = get_ocr_provider()

    t0 = time.perf_counter()
    lines = ocr.extract_from_image(img_path)
    t_ocr = time.perf_counter() - t0

    t1 = time.perf_counter()
    ocr_text = "\n".join([l["text"] for l in lines])
    clf = classify_report(ocr_text)
    rep_type = clf["report_type"]
    if expected_type:
        rep_type = expected_type
    parsed = route_report_parser(rep_type, ocr_text, ocr_lines=lines)
    t_parse = time.perf_counter() - t1

    t2 = time.perf_counter()
    summary_res = generate_health_summary(parsed)
    t_summary = time.perf_counter() - t2

    total_time = t_ocr + t_parse + t_summary
    print(f"Report Type Detected: {clf['report_type']} (used: {rep_type})")
    print(f"OCR Time: {t_ocr*1000:.1f}ms | Parsing Time: {t_parse*1000:.1f}ms | Summary Time: {t_summary*1000:.1f}ms | Total: {total_time*1000:.1f}ms")
    print(f"Biomarkers Found: {parsed.get('biomarkers_found', len(parsed.get('biomarkers', [])))}")
    print("-" * 80)
    header = f"{'Biomarker':<22} | {'Value':<7} | {'Unit':<8} | {'Final Reference':<16} | {'Ref Type':<12} | {'Source':<12} | {'Status':<10}"
    print(header)
    print("-" * 80)

    for bm in parsed.get("biomarkers", []):
        key = bm.get("key", "")
        val = str(bm.get("value", ""))
        unit = bm.get("unit") or bm.get("display_unit") or ""
        ref = bm.get("reference_range", "")
        s_ref = bm.get("structured_reference") or {}
        ref_type = s_ref.get("type") or "range"
        ref_source = bm.get("reference_source", "")
        status = bm.get("status", "")
        safe_ref = ref.encode('ascii', errors='replace').decode('ascii')
        print(f"{key:<22} | {val:<7} | {unit:<8} | {safe_ref:<16} | {ref_type:<12} | {ref_source:<12} | {status:<10}")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    images = [
        ("backend/tests/fixtures/ocr/original_aster_cbc.png", "CBC"),
        ("backend/tests/fixtures/ocr/original_care_diagnostics_lft.png", "LIVER_FUNCTION_TEST"),
        ("backend/tests/fixtures/ocr/original_care_diagnostics_kft.png", "KIDNEY_FUNCTION_TEST"),
    ]
    for path, exp in images:
        test_image(path, exp)
