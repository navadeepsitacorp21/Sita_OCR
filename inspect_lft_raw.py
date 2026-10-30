import sys
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
res, _ = engine("benchmark_data/lft_complete.png")
for item in res:
    print(f"[{item[2]}] {item[1]}")
