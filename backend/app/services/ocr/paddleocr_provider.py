import time
from typing import List, Dict, Any
from app.services.ocr.base_ocr import BaseOCRProvider

class PaddleOCRProvider(BaseOCRProvider):
    """
    PaddleOCR Provider (Fallback / Comparison / Legacy).
    """

    def __init__(self):
        t0 = time.perf_counter()
        from paddleocr import PaddleOCR
        self.engine = PaddleOCR(
            lang="en",
            enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        t_init = time.perf_counter() - t0
        print(f"[OCR INITIALIZATION] PaddleOCR provider initialized in {t_init*1000:.2f}ms")

    def extract_from_image(self, image_input: Any) -> List[Dict[str, Any]]:
        result = self.engine.ocr(image_input)
        ocr_lines = []
        if not result:
            return ocr_lines

        first = result[0]
        if isinstance(first, dict):
            texts = first.get("rec_texts", [])
            scores = first.get("rec_scores", [])
            boxes = first.get("dt_boxes", first.get("rec_boxes", []))
            for i, text in enumerate(texts):
                score = float(scores[i]) if i < len(scores) else 1.0
                bbox = boxes[i] if i < len(boxes) else []
                if hasattr(bbox, "tolist"):
                    bbox = bbox.tolist()
                ocr_lines.append({
                    "text": str(text).strip(),
                    "confidence": round(score, 4),
                    "bbox": bbox
                })
        elif isinstance(first, list):
            for line in first:
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    bbox = line[0] if hasattr(line[0], "tolist") else list(line[0])
                    text_score = line[1]
                    if isinstance(text_score, (list, tuple)):
                        text = text_score[0]
                        score = float(text_score[1]) if len(text_score) > 1 else 1.0
                    else:
                        text = str(text_score)
                        score = 1.0
                    ocr_lines.append({
                        "text": str(text).strip(),
                        "confidence": round(score, 4),
                        "bbox": bbox
                    })
        return ocr_lines
