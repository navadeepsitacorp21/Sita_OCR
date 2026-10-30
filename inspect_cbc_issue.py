import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.services.ocr_service import extract_text
from app.parsers.cbc_parser import CBCParser

class MockUpload:
    filename = 'Screenshot 2026-09-24 114550.png'
    async def read(self):
        with open(r'C:\Users\A Navadeep Reddy\Pictures\Screenshots\Screenshot 2026-09-24 114550.png', 'rb') as f:
            return f.read()

async def main():
    upload = MockUpload()
    res = await extract_text(upload)
    ocr_lines = res.get('ocr_lines', [])
    print(f"Total OCR lines: {len(ocr_lines)}")
    for i, l in enumerate(ocr_lines):
        print(f"[{i:02d}] {l.get('bbox')}: {l.get('text')}")
    
    parser = CBCParser()
    parsed = parser.parse(res.get('text', ''), ocr_lines)
    print("\nPARSED BIOMARKERS:")
    for bm in parsed.get('biomarkers', []):
        print(f"- {bm['key']}: {bm['name']} = {bm['value']} {bm['unit']} (Ref: {bm['reference_range']}, Status: {bm['status']})")

if __name__ == "__main__":
    asyncio.run(main())
