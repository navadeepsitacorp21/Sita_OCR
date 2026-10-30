import cv2, sys, os
sys.path.insert(0, 'backend')
from app.services.ocr import get_ocr_provider

img = cv2.imread(r'backend/tests/fixtures/ocr/original_aster_cbc.png')
ocr = get_ocr_provider()

for scale in [1.0, 1.5, 2.0]:
    if scale == 1.0:
        scaled_img = img
    else:
        scaled_img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    lines = ocr.extract_from_image(scaled_img)
    print(f"\n--- SCALE {scale} (Tokens: {len(lines)}) ---")
    for idx, l in enumerate(lines):
        t = l.get('text', '')
        if any(k in t.lower() for k in ['mono', 'mana', 'eos', 'lymp', 'lywp', 'neut', 'baso', 'wbc', 'plate', 'rbc', 'mcv', 'mch']):
            print(f"  [{idx:02d}] conf={l['confidence']:.2f} | text={t!r}")
