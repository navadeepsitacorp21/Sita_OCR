import cv2, sys
sys.path.insert(0, 'backend')
from app.services.ocr import get_ocr_provider

img = cv2.imread(r'backend/tests/fixtures/ocr/original_aster_cbc.png')
ocr = get_ocr_provider()

# Crop monocytes row (y: 340-365, x: 40-300)
row = img[342:365, 40:300]
cv2.imwrite('row_mono.png', row)

for interp in [cv2.INTER_CUBIC, cv2.INTER_LANCZOS4]:
    for fx in [1.5, 2.0, 2.5, 3.0]:
        r_up = cv2.resize(row, (0, 0), fx=fx, fy=fx, interpolation=interp)
        res = ocr.extract_from_image(r_up)
        txts = [f"{x['text']} ({x['confidence']:.2f})" for x in res]
        print(f"Interp {interp} Scale {fx}: {txts}")
