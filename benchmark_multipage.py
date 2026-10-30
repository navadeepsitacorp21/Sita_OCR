import asyncio
import os
import sys
import time
from fastapi import UploadFile

sys.path.insert(0, os.path.abspath("backend"))

from app.services.ocr_service import extract_text
from app.services.classifier_service import classify_report
from app.services.report_router import route_report_parser
from app.services.health_summary_service import generate_health_summary
from app.database import SessionLocal, create_report

class MockUploadFile:
    def __init__(self, filepath):
        self.filename = os.path.basename(filepath)
        self.filepath = filepath

    async def read(self):
        with open(self.filepath, "rb") as f:
            return f.read()


async def run_multipage_benchmarks():
    print("=" * 60)
    print("SITA OCR MULTI-PAGE PDF BENCHMARK (RapidOCR ONNX)")
    print("=" * 60)

    test_files = [
        ("Digital PDF (3p)", "benchmark_data/multipage/digital_3p.pdf"),
        ("Scanned PDF (1p)", "benchmark_data/multipage/scanned_1p.pdf"),
        ("Scanned PDF (3p)", "benchmark_data/multipage/scanned_3p.pdf"),
        ("Scanned PDF (5p)", "benchmark_data/multipage/scanned_5p.pdf"),
        ("Scanned PDF (10p)", "benchmark_data/multipage/scanned_10p.pdf"),
    ]

    for label, path in test_files:
        mock_file = MockUploadFile(path)
        t0 = time.perf_counter()
        result = await extract_text(mock_file)
        t_total = time.perf_counter() - t0

        perf = result["performance"]
        print(f"\nReport: {label}")
        print(f"  Pages: {result['page_count']}")
        print(f"  OCR Invocations: {perf['ocr_calls']}")
        print(f"  Digital Fastpath: {result.get('is_digital_fastpath')}")
        print(f"  OCR Inference: {perf['ocr_inference_ms']:.1f} ms")
        print(f"  Total Extraction: {t_total*1000:.1f} ms ({t_total:.2f} s)")

        # Verify parsing and Health Vault compatibility
        ocr_text = result["text"]
        clf = classify_report(ocr_text)
        parsed = route_report_parser(clf["report_type"], ocr_text, ocr_lines=result["ocr_lines"])
        summary = generate_health_summary(parsed)

        db = SessionLocal()
        payload = {
            "filename": os.path.basename(path),
            "page_count": result["page_count"],
            "ocr_summary": {"average_confidence": result["average_confidence"]},
            "classification": clf,
            "parsed_report": parsed,
            "health_summary": summary,
            "health_highlights": {"highlights": []}
        }
        saved = create_report(db, payload)
        db.close()

        print(f"  Parsed Biomarkers: {parsed.get('biomarkers_found')}")
        print(f"  Health Vault Saved: Report ID {saved.report_id}")


if __name__ == "__main__":
    asyncio.run(run_multipage_benchmarks())
