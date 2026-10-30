import os, sys, json

backend_dir = os.path.join(os.getcwd(), "backend")
sys.stdout.reconfigure(encoding='utf-8')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary

img_path = os.path.join(backend_dir, "tests", "fixtures", "ocr", "original_care_diagnostics_kft.png")
ocr = get_ocr_provider()
lines = ocr.extract_from_image(img_path)
print(f"Total OCR tokens: {len(lines)}")

print("\n--- ALL RAW OCR TOKENS ---")
for idx, l in enumerate(lines):
    b = l.get("bbox", [])
    xs = [p[0] for p in b] if b else [0]
    ys = [p[1] for p in b] if b else [0]
    t_safe = l.get("text", "").encode("ascii", "replace").decode("ascii")
    print(f"[{idx:02d}] y={min(ys):5.1f}..{max(ys):5.1f} | x={min(xs):5.1f}..{max(xs):5.1f} | conf={l.get('confidence'):.2f} | text={t_safe!r}")

ocr_text = "\n".join([l["text"] for l in lines])
clf = classify_report(ocr_text)
print(f"\nClassification: {clf}")

parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=lines)
print(f"\nParsed report type: {parsed.get('report_type')}")
print(f"Parser version: {parsed.get('parser_version')}")
print(f"Biomarkers found ({parsed.get('biomarkers_found')}):")
for b in parsed.get("biomarkers", []):
    ref_safe = str(b.get("reference_range", "")).encode("ascii", "replace").decode("ascii")
    print(f"  {b.get('key'):<25} | {b.get('name')} | val={b.get('value')} {b.get('unit')} | status={b.get('status')} | ref={ref_safe!r}")

print(f"\nBiomarkers missing: {parsed.get('biomarkers_missing')}")
summary = generate_health_summary(parsed)
print(f"Health Summary: {summary}")
