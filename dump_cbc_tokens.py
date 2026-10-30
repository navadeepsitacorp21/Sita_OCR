import sys, os
sys.path.insert(0, 'backend')
from app.services.ocr import get_ocr_provider

img_path = r'backend/tests/fixtures/ocr/original_aster_cbc.png'
ocr = get_ocr_provider()
lines = ocr.extract_from_image(img_path)

print(f"Total tokens: {len(lines)}")
for idx in range(35, 105):
    if idx < len(lines):
        l = lines[idx]
        b = l.get("bbox", [])
        xs = [p[0] for p in b] if b else [0]
        ys = [p[1] for p in b] if b else [0]
        print(f"[{idx:03d}] y={min(ys):5.1f}..{max(ys):5.1f} | x={min(xs):5.1f}..{max(xs):5.1f} | conf={l.get('confidence'):.2f} | text={l.get('text')!r}")
