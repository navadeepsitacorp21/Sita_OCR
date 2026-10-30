import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from inspect_cbc_issue import MockUpload
import asyncio
from app.services.ocr_service import extract_text
from app.parsers.cbc_parser import CBCParser, get_token_geometry
from app.utils.alias_resolver import resolve_biomarker_alias
from app.utils.cbc_registry import CBC_BIOMARKERS

async def trace_spatial():
    upload = MockUpload()
    res = await extract_text(upload)
    ocr_lines = res.get('ocr_lines', [])
    parser = CBCParser()
    
    tokens = []
    for idx, item in enumerate(ocr_lines):
        text = (item.get("text") or "").strip()
        conf = float(item.get("confidence", 1.0))
        bbox = item.get("bbox", [])
        x_min, y_min, x_max, y_max = get_token_geometry(bbox)
        tokens.append({
            "id": idx,
            "text": text,
            "confidence": conf,
            "bbox": bbox,
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "y_center": (y_min + y_max) / 2.0,
            "x_center": (x_min + x_max) / 2.0,
            "height": max(1.0, y_max - y_min)
        })

    for t in tokens:
        resolved = resolve_biomarker_alias(t["text"], allowed_keys=parser.cat_allowed_keys)
        if resolved:
            print(f"Token [{t['id']}] '{t['text']}' (x={t['x_min']:.1f}, y={t['y_center']:.1f}, h={t['height']:.1f}) -> {resolved['canonical_key']}")
            # find row tokens
            tolerance = min(5.0, max(2.5, t["height"] * 0.45))
            row_tokens = [tok for tok in tokens if abs(tok["y_center"] - t["y_center"]) <= tolerance]
            row_tokens.sort(key=lambda tok: tok["x_min"])
            print("   Row tokens:", [(rt["id"], rt["text"], f"x={rt['x_min']:.1f}") for rt in row_tokens])

asyncio.run(trace_spatial())
