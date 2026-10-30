import time
from typing import List, Dict, Any
from app.services.ocr.base_ocr import BaseOCRProvider

class RapidOCRProvider(BaseOCRProvider):
    """
    RapidOCR ONNX Runtime Provider.
    Executes lightweight C++ vectorized ONNX models on CPU with high parallelism.
    """

    def __init__(self):
        t0 = time.perf_counter()
        from rapidocr_onnxruntime import RapidOCR
        self.engine = RapidOCR(use_angle_cls=False)
        t_init = time.perf_counter() - t0
        print(f"[OCR INITIALIZATION] RapidOCR ONNX provider initialized in {t_init*1000:.2f}ms")

    def extract_from_image(self, image_input: Any) -> List[Dict[str, Any]]:
        ocr_res, elapse = self.engine(image_input)
        ocr_lines = []
        if not ocr_res:
            return ocr_lines

        for item in ocr_res:
            # RapidOCR output item: [bbox, text, score]
            bbox = item[0] if len(item) > 0 else []
            text = item[1] if len(item) > 1 else ""
            score = float(item[2]) if len(item) > 2 else 1.0

            # Convert numpy types to native Python types
            if hasattr(bbox, "tolist"):
                bbox = bbox.tolist()

            ocr_lines.append({
                "text": str(text).strip(),
                "confidence": round(score, 4),
                "bbox": bbox
            })
        return ocr_lines
