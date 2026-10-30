import sys
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
res, _ = engine("benchmark_data/lft_complete.png")
lines = [{"text": r[1], "conf": float(r[2]), "bbox": r[0]} for r in res]
for l in lines:
    b = l["bbox"]
    y_min = min(p[1] for p in b)
    y_max = max(p[1] for p in b)
    x_min = min(p[0] for p in b)
    x_max = max(p[0] for p in b)
    print(f"y: {y_min:5.1f}..{y_max:5.1f} | x: {x_min:5.1f}..{x_max:5.1f} | conf: {l['conf']:.2f} | text: {l['text']}")
