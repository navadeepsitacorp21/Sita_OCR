import os
import sys
import json
from rapidocr_onnxruntime import RapidOCR

sys.path.insert(0, "backend")
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser

engine = RapidOCR()
files = [
    ("Aster CBC", "benchmark_data/aster_cbc.png"),
    ("Labsmart CBC", "benchmark_data/labsmart_cbc.png"),
    ("Care Diagnostics LFT", "benchmark_data/lft_complete.png")
]

for name, path in files:
    res, elapse = engine(path)
    ocr_lines = []
    if res:
        for item in res:
            bbox = item[0].tolist() if hasattr(item[0], "tolist") else item[0]
            ocr_lines.append({"text": item[1], "confidence": float(item[2]), "bbox": bbox})
    ocr_text = "\n".join([l["text"] for l in ocr_lines])
    clf = classify_report(ocr_text)
    parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=ocr_lines)
    print("=" * 40)
    print(f"=== {name} ===")
    print("Report Type:", clf["report_type"])
    print("Biomarkers found:", parsed.get("biomarkers_found"))
    for b in parsed.get("biomarkers", []):
        k = b.get("key")
        val = b.get("value")
        unit = b.get("unit")
        status = b.get("status")
        print(f"  {k}: {val} {unit} [status: {status}]")
