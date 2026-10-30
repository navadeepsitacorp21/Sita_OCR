import time
import cv2
import numpy as np
from typing import List, Dict, Any
from app.services.ocr.base_ocr import BaseOCRProvider


def detect_and_filter_table_grid(img: np.ndarray, dt_boxes: np.ndarray) -> np.ndarray:
    """
    Generic layout-aware bounding box filter for structured multi-column grid tables.
    Detects table borders and vertical column dividers using morphological operations.
    If a structured table with >= 6 columns is detected (e.g., standard clinical lab tables
    with Test Name, Results, Reference Range, Units, Specimen, Method):
      - Filters out methodology/technique column (col 6) since clinical parsing only needs
        biomarker name, observed value, unit, and reference interval.
      - Filters out post-table disclaimer and hospital administrative footer text blocks.
    For borderless tables or tables with < 6 columns (e.g. LFT, KFT):
      - Retains 100% of detected boxes.
    """
    if dt_boxes is None or len(dt_boxes) == 0:
        return dt_boxes

    try:
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        bw = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

        # Detect horizontal grid lines (> 30% width)
        h_k = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.3), 1))
        h_line = cv2.dilate(cv2.erode(bw, h_k), h_k)

        # Detect vertical grid lines (> 100px)
        v_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 100))
        v_line = cv2.dilate(cv2.erode(bw, v_k), v_k)

        table_mask = cv2.bitwise_or(h_line, v_line)
        cnts, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_grid = None
        for c in cnts:
            bx, by, bw_box, bh_box = cv2.boundingRect(c)
            if bw_box > w * 0.5 and bh_box > 100:
                tbl_v = v_line[by:by + bh_box, bx:bx + bw_box]
                v_cnts, _ = cv2.findContours(tbl_v, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                v_cols = [bx + cv2.boundingRect(vc)[0] for vc in v_cnts if cv2.boundingRect(vc)[3] > bh_box * 0.5]
                v_cols.sort()
                merged_cols = []
                for x in v_cols:
                    if not merged_cols or x - merged_cols[-1] > 5:
                        merged_cols.append(x)
                if len(merged_cols) >= 7:  # >= 6 columns requires at least 7 vertical divider lines
                    table_grid = {
                        "y_top": by,
                        "y_bottom": by + bh_box,
                        "method_col_x": merged_cols[-2],
                    }
                    break

        if not table_grid:
            return dt_boxes

        y_bottom = table_grid["y_bottom"]
        method_col_x = table_grid["method_col_x"]

        kept_boxes = []
        for box in dt_boxes:
            ymin = box[:, 1].min()
            xmin = box[:, 0].min()

            # Filter out post-table administrative/disclaimer text blocks
            if ymin > y_bottom + 15:
                continue

            # Filter out methodology column within table
            if table_grid["y_top"] <= ymin <= y_bottom and xmin >= method_col_x - 5:
                continue

            kept_boxes.append(box)

        return np.array(kept_boxes) if len(kept_boxes) > 0 else dt_boxes
    except Exception:
        return dt_boxes


class RapidOCRProvider(BaseOCRProvider):
    """
    RapidOCR ONNX Runtime Provider.
    Executes lightweight C++ vectorized ONNX models on CPU with high parallelism.
    Configured with rec_batch_num=12 and layout-aware pre-recognition filtering.
    """

    def __init__(self):
        t0 = time.perf_counter()
        from rapidocr_onnxruntime import RapidOCR
        self.engine = RapidOCR(use_angle_cls=False, text_score=0.3)
        self.engine.text_recognizer.rec_batch_num = 12
        # Pre-warm ONNX execution providers with a minimal dummy image so the first upload doesn't hit a cold-start penalty
        try:
            dummy = np.zeros((64, 64, 3), dtype=np.uint8)
            self.engine(dummy)
        except Exception:
            pass
        t_init = time.perf_counter() - t0
        print(f"[OCR INITIALIZATION] RapidOCR ONNX provider initialized in {t_init*1000:.2f}ms")

    def extract_from_image(self, image_input: Any) -> List[Dict[str, Any]]:
        img = self.engine.load_img(image_input)
        h, w = img.shape[:2]

        # Automatic downscaling for high-resolution images (> 2048px) to prevent CPU timeouts
        # Coordinates are mapped back to original image scale so downstream token geometry is 100% preserved.
        scale = 1.0
        max_dim = max(h, w)
        if max_dim > 2048:
            scale = 2048.0 / max_dim
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        dt_boxes, det_elapse = self.engine.text_detector(img)
        if dt_boxes is None or len(dt_boxes) < 1:
            return []

        dt_boxes = self.engine.sorted_boxes(dt_boxes)
        dt_boxes = detect_and_filter_table_grid(img, dt_boxes)

        img_crop_list = self.engine.get_crop_img_list(img, dt_boxes)
        rec_res, rec_elapse = self.engine.text_recognizer(img_crop_list)

        filter_boxes, filter_rec_res = self.engine.filter_boxes_rec_by_score(dt_boxes, rec_res)
        if not filter_boxes:
            return []

        ocr_lines = []
        for dt, rec in zip(filter_boxes, filter_rec_res):
            if scale != 1.0:
                dt_rescaled = dt / scale
                bbox = dt_rescaled.tolist() if hasattr(dt_rescaled, "tolist") else dt_rescaled
            else:
                bbox = dt.tolist() if hasattr(dt, "tolist") else dt
            text = rec[0]
            score = float(rec[1])

            ocr_lines.append({
                "text": str(text).strip(),
                "confidence": round(score, 4),
                "bbox": bbox
            })
        return ocr_lines

