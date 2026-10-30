import os, sys

backend_dir = os.path.join(os.getcwd(), "backend")
sys.stdout.reconfigure(encoding='utf-8')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ocr import get_ocr_provider
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary

img_path = os.path.join(backend_dir, "tests", "fixtures", "ocr", "original_aster_cbc.png")
if not os.path.exists(img_path):
    img_path = r"C:\Users\A Navadeep Reddy\Pictures\Screenshots\Screenshot 2026-09-24 114601.png"

print("Image path:", img_path)
ocr = get_ocr_provider()
lines = ocr.extract_from_image(img_path)
print(f"Total OCR tokens: {len(lines)}")

text = "\n".join([l["text"] for l in lines])
clf = classify_report(text)
print("Classification:", clf)

parsed = route_report_parser(clf["report_type"], text, ocr_lines=lines)
print(f"Biomarkers found: {len(parsed['biomarkers'])}")
for b in parsed["biomarkers"]:
    print(f"  {b['key']:<20}: {b['value']} {b['unit']} (status: {b['status']}, ref: {b['reference_range']})")

summary = generate_health_summary(parsed)
print("Health Summary:", summary)
