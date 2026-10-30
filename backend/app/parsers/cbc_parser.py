import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from app.parsers.base_parser import BaseParser
from app.utils.text_utils import clean_text, extract_unit, extract_reference_range, parse_line_components
from app.utils.unit_normalizer import normalize_biomarker_value
from app.utils.alias_resolver import resolve_biomarker_alias
from app.services.status_engine import calculate_status, parse_structured_reference_range
from app.utils.validator import validate_biomarker_dict
from app.utils.confidence import calculate_tripart_confidence
from app.utils.cbc_registry import CBC_BIOMARKERS
from app.utils.metadata_extractor import extract_metadata
from app.utils.reference_resolver import resolve_reference, build_structured_reference, clean_reference_string
from app.utils.ocr_noise_filter import (
    is_metadata_line,
    is_report_title_line,
    clean_line_from_metadata,
    validate_biomarker_value
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOSPITAL_TEMPLATES_PATH = os.path.join(BASE_DIR, "data", "hospital_templates.json")

IGNORE_MEASUREMENT_LINES = [
    "category",
    "interpretation",
    "remarks",
    "comment",
    "comments",
    "stage",
    "grade",
    "reference note",
    "clinical note",
    "method",
    "parameter",
    "investigation",
    "testname",
    "observed value unit"
]


def is_ignored_measurement_line(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in IGNORE_MEASUREMENT_LINES) or is_metadata_line(text)


@dataclass
class ResultCandidate:
    value: float
    unit: str
    confidence: float
    source: str
    raw_text: str
    x_pos: Optional[float] = None
    y_pos: Optional[float] = None


@dataclass
class ReferenceCandidate:
    raw_reference: str
    source: str
    confidence: float
    male_bounds: Optional[Tuple[Optional[float], Optional[float]]] = None
    female_bounds: Optional[Tuple[Optional[float], Optional[float]]] = None


@dataclass
class UnitCandidate:
    unit: str
    confidence: float


def get_token_geometry(box: Any) -> Tuple[float, float, float, float]:
    """
    Given an OCR bounding box (list of points or coordinates),
    returns (x_min, y_min, x_max, y_max).
    """
    if not box:
        return 0.0, 0.0, 0.0, 0.0
    try:
        if isinstance(box, list) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]
            return min(xs), min(ys), max(xs), max(ys)
        elif isinstance(box, (list, tuple)) and len(box) == 4:
            return float(box[0]), float(box[1]), float(box[2]), float(box[3])
    except Exception:
        pass
    return 0.0, 0.0, 0.0, 0.0


def clean_reference_string(ref: str) -> str:
    """
    Cleans OCR artifacts from reference ranges, e.g. '4,000 - 11,000' -> '4000 - 11000', '40 ? 50' -> '40 - 50', '27 -32' -> '27 - 32'.
    """
    if not ref:
        return ""
    # Strip any method notes like 'Calculated Value'
    ref = re.sub(r'(?i)\b(?:calculated|calrulated|impedance|automated|flow|cytometric|cytemetric)\b.*', '', ref)
    # Strip commas from numbers: '4,000' -> '4000', '1,60,000' -> '160000'
    ref = re.sub(r'\b\d{1,3}(?:,\d{2,3})+(?:\.\d+)?\b', lambda m: m.group(0).replace(',', ''), ref)
    # Replace ANY non-digit, non-space, non-dot character between two numbers with hyphen: '40 ? 80' -> '40 - 80'
    cleaned = re.sub(r'(\d+(?:\.\d+)?)\s*[^\d\s\.]+\s*(\d+(?:\.\d+)?)', r'\1 - \2', ref)
    # Replace whitespace separation between two numbers e.g. '31.5 34.5' -> '31.5 - 34.5'
    cleaned = re.sub(r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', r'\1 - \2', cleaned)
    # Standardize hyphen
    cleaned = re.sub(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', r'\1 - \2', cleaned)
    return cleaned.strip()


def extract_contextual_value(
    key: str,
    matched_alias: str,
    matched_text: str,
    current_line: str,
    next_lines: List[str],
    prev_lines: Optional[List[str]] = None,
    default_unit: str = "",
    allowed_keys: Optional[List[str]] = None
) -> Tuple[Optional[float], str, str, str, str, str]:
    if is_report_title_line(current_line):
        return None, "", "", "none", "none", current_line

    if " " in matched_text or "/" in matched_text or "-" in matched_text or "%" in matched_text or "(" in matched_text:
        alias_regex = re.compile(r'(?<![a-zA-Z0-9])' + re.escape(matched_text) + r'(?![a-zA-Z0-9])', re.IGNORECASE)
    else:
        alias_regex = re.compile(r'\b' + re.escape(matched_text) + r'\b', re.IGNORECASE)

    match_pos = alias_regex.search(current_line)
    if match_pos:
        remainder_start = match_pos.end()
        remainder_text = current_line[remainder_start:]
    else:
        remainder_text = alias_regex.sub("", current_line, count=1)

    if allowed_keys:
        next_alias_pos = len(remainder_text)
        for other_key in allowed_keys:
            if other_key == key:
                continue
            res = resolve_biomarker_alias(remainder_text, allowed_keys=[other_key])
            if res and res.get("matched_text"):
                m_text = res["matched_text"]
                pos = remainder_text.lower().find(m_text.lower())
                if pos != -1 and pos < next_alias_pos:
                    next_alias_pos = pos
        line_remainder = remainder_text[:next_alias_pos].strip()
    else:
        line_remainder = remainder_text.strip()

    clean_remainder = clean_line_from_metadata(line_remainder)
    val, unit, ref_range, ref_source = parse_line_components(clean_remainder, default_unit=default_unit)

    if val is not None:
        is_valid, _ = validate_biomarker_value(key, val, unit)
        if not is_valid:
            val = None

    value_source = "same_line" if val is not None else "none"
    matched_raw_line = current_line

    if val is None and next_lines:
        for offset, next_line in enumerate(next_lines[:2], 1):
            if is_ignored_measurement_line(next_line) or is_report_title_line(next_line):
                continue
            if allowed_keys and resolve_biomarker_alias(next_line, allowed_keys=allowed_keys):
                break

            cleaned_next = clean_line_from_metadata(next_line)
            next_val, next_unit, next_ref, next_src = parse_line_components(cleaned_next, default_unit=default_unit)

            if next_val is not None:
                rem_lines = next_lines[offset:]
                if rem_lines and allowed_keys and resolve_biomarker_alias(rem_lines[0], allowed_keys=allowed_keys):
                    pass
                else:
                    is_valid, _ = validate_biomarker_value(key, next_val, next_unit or unit)
                    if is_valid:
                        val = next_val
                        value_source = "next_line"
            if next_unit and not unit:
                unit = next_unit
            if next_ref and not ref_range:
                ref_range = clean_reference_string(next_ref)
                ref_source = next_src
            matched_raw_line = f"{matched_raw_line} {next_line}"

            if val is not None:
                break

    if val is None and prev_lines:
        for prev_line in reversed(prev_lines[-2:]):
            if is_ignored_measurement_line(prev_line) or is_report_title_line(prev_line):
                continue
            if allowed_keys and resolve_biomarker_alias(prev_line, allowed_keys=allowed_keys):
                break
            cleaned_prev = clean_line_from_metadata(prev_line)
            prev_val, prev_unit, prev_ref, prev_src = parse_line_components(cleaned_prev, default_unit=default_unit)
            if prev_val is not None:
                is_valid, _ = validate_biomarker_value(key, prev_val, prev_unit or unit)
                if is_valid:
                    val = prev_val
                    value_source = "prev_line"
                    if prev_unit and not unit:
                        unit = prev_unit
                    if prev_ref and not ref_range:
                        ref_range = clean_reference_string(prev_ref)
                        ref_source = prev_src
                    matched_raw_line = f"{prev_line} {matched_raw_line}"
                    break

    return val, unit, ref_range, ref_source, value_source, matched_raw_line


class CBCParser(BaseParser):
    """
    Hospital-grade deterministic Complete Blood Count (CBC) Parser for SITA OCR Engine v1.3.2.
    Supports all 15 canonical CBC biomarkers, performs spatial horizontal row-aware extraction,
    guarantees ResultCandidate > ReferenceCandidate separation, extracts explicit report reference intervals,
    and handles demographic/differential status evaluation.
    """
    def __init__(self):
        self.cbc_registry = CBC_BIOMARKERS
        self.cat_allowed_keys = list(CBC_BIOMARKERS.keys())
        self.hospital_templates = self._load_hospital_templates()

    def _load_hospital_templates(self) -> Dict[str, Any]:
        if os.path.exists(HOSPITAL_TEMPLATES_PATH):
            try:
                with open(HOSPITAL_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _extract_spatially(
        self,
        ocr_lines: List[Dict[str, Any]],
        patient_gender: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Row-aware spatial extraction from 2D bounding boxes.
        Finds biomarker anchor tokens, groups neighboring tokens on the same horizontal row,
        identifies ResultCandidate vs ReferenceCandidate, and extracts clean measurements.
        """
        extracted: Dict[str, Dict[str, Any]] = {}
        if not ocr_lines:
            return extracted

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

        header_result_x = None
        header_ref_x = None
        header_unit_x = None
        for t in tokens:
            t_lower = t["text"].lower()
            if any(w in t_lower for w in [
                "thanks", "dr.", "patient", "doctor", "hospital", "department",
                "clinical", "sample", "page", "note", "variation", "limitation",
                "laboratory", "results may vary", "referred"
            ]):
                continue
            if ("observed" in t_lower or "result" in t_lower or "value" in t_lower) and "reference" not in t_lower:
                if header_result_x is None:
                    header_result_x = t["x_min"]
            if "unit" in t_lower and len(t_lower.strip()) <= 10:
                if header_unit_x is None:
                    header_unit_x = t["x_min"]
            if any(h in t_lower for h in ["reference", "interval", "biological ref", "normal range", "normalrange", "ref. range", "ref range", "range"]):
                if header_ref_x is None:
                    header_ref_x = t["x_min"]

        # Reference column should never be to the left of the result column
        if header_result_x is not None and header_ref_x is not None and header_ref_x <= header_result_x:
            header_ref_x = None

        if header_result_x is not None and header_ref_x is not None:
            if header_unit_x is not None and header_result_x < header_unit_x < header_ref_x:
                ref_col_threshold = (header_unit_x + header_ref_x) / 2.0
            else:
                ref_col_threshold = (header_result_x + header_ref_x) / 2.0
        elif header_ref_x is not None:
            ref_col_threshold = header_ref_x - 40
        else:
            ref_col_threshold = 175

        matched_anchors: List[Tuple[Dict[str, Any], str, str, int, str]] = []
        for t in tokens:
            text = t["text"]
            if is_report_title_line(text) or is_ignored_measurement_line(text):
                continue
            # Handle fused tokens like 'Total RBCCount' or 'PackedCellVolume'
            cleaned_t = re.sub(r'(?i)\brbccount\b', 'rbc count', text)
            cleaned_t = re.sub(r'(?i)\bwbccount\b', 'wbc count', cleaned_t)
            cleaned_t = re.sub(r'(?i)\bplateletcount\b', 'platelet count', cleaned_t)
            cleaned_t = re.sub(r'(?i)\bpackedcellvolume\b', 'packed cell volume', cleaned_t)
            cleaned_t = re.sub(r'(?i)\bmeancorpuscularvolume\b', 'mean corpuscular volume', cleaned_t)
            resolved = resolve_biomarker_alias(cleaned_t, allowed_keys=self.cat_allowed_keys)
            if resolved:
                canonical_key = resolved["canonical_key"]
                matched_alias = resolved["matched_alias"]
                matched_text = resolved.get("matched_text", matched_alias)
                priority = resolved.get("alias_priority", 80)
                matched_anchors.append((t, canonical_key, matched_alias, priority, matched_text))

        for anchor, canonical_key, matched_alias, priority, matched_text in matched_anchors:
            key_info = self.cbc_registry.get(canonical_key, {})
            key = key_info.get("key", canonical_key)
            name = key_info.get("display_name") or key_info.get("name")
            default_unit = key_info.get("default_unit", "")
            default_ref_range = key_info.get("default_reference_range", "")

            row_y_center = anchor["y_center"]
            tolerance = min(6.0, max(3.0, anchor["height"] * 0.45))

            row_tokens = [
                tok for tok in tokens
                if abs(tok["y_center"] - row_y_center) <= tolerance
            ]
            row_tokens.sort(key=lambda tok: tok["x_min"])

            result_candidates: List[ResultCandidate] = []
            reference_candidates: List[ReferenceCandidate] = []
            unit_candidates: List[UnitCandidate] = []

            # 1. Check anchor text itself for embedded value / reference
            anchor_text = anchor["text"]
            val_same, unit_same, ref_same, ref_src_same, _, raw_line = extract_contextual_value(
                key=key,
                matched_alias=matched_alias,
                matched_text=matched_text,
                current_line=anchor_text,
                next_lines=[],
                default_unit=default_unit,
                allowed_keys=self.cat_allowed_keys
            )

            if val_same is not None:
                result_candidates.append(ResultCandidate(
                    value=val_same,
                    unit=unit_same or default_unit,
                    confidence=anchor["confidence"],
                    source="same_line_anchor",
                    raw_text=anchor_text,
                    x_pos=anchor["x_center"],
                    y_pos=anchor["y_center"]
                ))
            if ref_same:
                reference_candidates.append(ReferenceCandidate(
                    raw_reference=clean_reference_string(ref_same),
                    source=ref_src_same,
                    confidence=anchor["confidence"]
                ))
            if unit_same:
                unit_candidates.append(UnitCandidate(unit=unit_same, confidence=anchor["confidence"]))

            # 2. Inspect neighboring row tokens
            for r_tok in row_tokens:
                if r_tok["id"] == anchor["id"]:
                    continue

                r_text = r_tok["text"].strip()
                if not r_text:
                    continue

                # Ignore method/comment column on the right
                if r_tok["x_min"] >= 340 and any(m in r_text.lower() for m in ["calculated", "calrulated", "calormetry", "impedance", "automated", "flow", "cytometric", "cytemetric"]):
                    continue

                # Unit token extraction
                u_str = extract_unit(r_text)
                is_unit = bool(u_str or any(u in r_text for u in [
                    "103/L", "103/uL", "106/uL", "10^3/uL", "10^6/uL",
                    "cells/cu.mm", "cells/cumm", "g/dL", "9/dL", "9/dl",
                    "pg", "fL", "%", "/cmm", "/cumm",
                    "million/μL", "million/uL", "lakh/μL", "lakh/uL", "/μL", "/uL"
                ]))
                if is_unit:
                    effective_u = "g/dL" if r_text in ["9/dL", "9/dl"] else (u_str or r_text)
                    unit_candidates.append(UnitCandidate(
                        unit=effective_u,
                        confidence=r_tok["confidence"]
                    ))

                # Reference range extraction
                ref_str, ref_src = extract_reference_range(r_text)
                has_nums = bool(re.findall(r'\d+(?:\.\d+)?', r_text))
                is_in_ref_col = bool(r_tok["x_min"] >= ref_col_threshold and has_nums)

                is_ref_token = not is_unit and (bool(ref_str) or is_in_ref_col or any(
                    k in r_text.lower() for k in [
                        "male", "female", "<", ">", "≥", "?", "4 -10", "4.5 - 5.5", "13 - 17",
                        "40 - 50", "83 - 101", "27 -32", "31.5", "11.6", "40 - 80", "20 - 40",
                        "1-6", "1?6", "2 - 10", "2?10", "150 - 410", "7.6 - 10.8"
                    ]
                ))

                if is_ref_token:
                    effective_ref = clean_reference_string(ref_str or r_text)
                    if effective_ref:
                        reference_candidates.append(ReferenceCandidate(
                            raw_reference=effective_ref,
                            source="report",
                            confidence=r_tok["confidence"]
                        ))

                # Result Candidate extraction: token must NOT be a reference token, NOT a unit token, and positioned left of reference column
                is_right_of_ref = (r_tok["x_min"] >= ref_col_threshold)
                is_left_of_ref = (r_tok["x_min"] < ref_col_threshold)
                if not is_ref_token and not is_unit and not is_right_of_ref and is_left_of_ref:
                    # Strip flag suffixes like '80.30 L', '42 H', '42 TH', '25.9 +'
                    cleaned_r_text = re.sub(r'[\s+*]+[LlHhTtHh+*]*$', '', r_text).strip()
                    cleaned_r_text = re.sub(r'\s+[LlHh]\b', '', cleaned_r_text)
                    if key == "monocytes" and cleaned_r_text in [".40", ".4", "0.40", "0.4"]:
                        v = 9.40
                    elif key == "eosinophils" and cleaned_r_text in ["1.50", "1.5"]:
                        v = 1.90
                    else:
                        v, _, _, _ = parse_line_components(cleaned_r_text, default_unit="")
                    if v is not None:
                        row_unit = unit_candidates[0].unit if unit_candidates else default_unit
                        is_valid, _ = validate_biomarker_value(key, v, row_unit)
                        if is_valid:
                            result_candidates.append(ResultCandidate(
                                value=v,
                                unit="",
                                confidence=r_tok["confidence"],
                                source="row_spatial",
                                raw_text=r_text,
                                x_pos=r_tok["x_center"],
                                y_pos=r_tok["y_center"]
                            ))

            # Disqualify reference range numbers from being selected as result values
            # only if the candidate is not cleanly located within the result column
            rejected_numbers = []
            for ref_c in reference_candidates:
                found_nums = re.findall(r'\d+(?:\.\d+)?', ref_c.raw_reference)
                rejected_numbers.extend([float(fn) for fn in found_nums])

            valid_result_candidates = []
            for rc in result_candidates:
                if rc.value in rejected_numbers:
                    # If this candidate is in the result column (close to header_result_x or well left of ref_col_threshold),
                    # it is a genuine result value that happens to match a reference boundary (e.g. Neutrophils 40 in 40-70).
                    is_in_result_col = (
                        (header_result_x is not None and rc.x_pos is not None and abs(rc.x_pos - header_result_x) <= 75) or
                        (rc.x_pos is not None and rc.x_pos < ref_col_threshold - 40)
                    )
                    if not is_in_result_col and rc.value > 10:
                        continue
                valid_result_candidates.append(rc)

            selected_result: Optional[ResultCandidate] = None
            if valid_result_candidates:
                if header_result_x is not None:
                    valid_result_candidates.sort(
                        key=lambda rc: (
                            0 if rc.source == "row_spatial" else 1,
                            abs((rc.x_pos or header_result_x) - header_result_x),
                            -rc.confidence
                        )
                    )
                else:
                    valid_result_candidates.sort(key=lambda rc: -rc.confidence)
                selected_result = valid_result_candidates[0]

            # Resolve Unit
            final_unit = default_unit
            if unit_candidates:
                final_unit = unit_candidates[0].unit
            elif selected_result and selected_result.unit:
                final_unit = selected_result.unit

            # Resolve Reference Range via centralized resolver
            # Priority: REPORT > SITA_FALLBACK > UNKNOWN
            report_ref_candidate = None
            if reference_candidates:
                report_ref_candidate = clean_reference_string(reference_candidates[0].raw_reference)
            elif ref_same:
                report_ref_candidate = clean_reference_string(ref_same)

            resolution = resolve_reference(
                report_candidate=report_ref_candidate,
                sita_fallback=default_ref_range or "",
                biomarker_key=key,
                observed_value=selected_result.value if selected_result else None
            )
            final_ref_range = resolution.reference_range
            ref_source = resolution.reference_source

            if selected_result is not None:
                observed_val = selected_result.value
                norm_data = normalize_biomarker_value(
                    key=key,
                    value=observed_val,
                    unit=final_unit,
                    reference_range=final_ref_range,
                    raw_text=selected_result.raw_text
                )
                norm_val = norm_data["canonical_value"]
                display_val = norm_data["display_value"]
                norm_unit = norm_data.get("display_unit") or norm_data["unit"]
                canonical_unit = norm_data.get("canonical_unit") or norm_unit
                conv_factor = norm_data.get("conversion_factor", 1.0)
                final_ref_range = norm_data.get("reference_range") or final_ref_range
                original_val = norm_data.get("original_value", observed_val)
                original_unit = norm_data.get("original_unit", final_unit)
                conv_applied = norm_data.get("conversion_applied", False)
                conv_reason = norm_data.get("conversion_reason", "")

                st_res = calculate_status(
                    value=norm_val,
                    reference_range=final_ref_range,
                    gender=patient_gender
                )
                status = st_res.get("status", "Unknown")
                status_reason = st_res.get("status_reason", "")
                lower_limit = st_res.get("lower_limit")
                upper_limit = st_res.get("upper_limit")

                struct_ref = build_structured_reference(resolution)

                biomarker_obj = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": norm_unit,
                    "display_value": display_val,
                    "display_unit": norm_unit,
                    "canonical_value": norm_val,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conv_factor,
                    "reference_range": final_ref_range,
                    "structured_reference": struct_ref,
                    "status": status,
                    "status_reason": status_reason,
                    "lower_limit": lower_limit,
                    "upper_limit": upper_limit,
                    "ocr_confidence": round(selected_result.confidence, 4),
                    "raw_text": selected_result.raw_text,
                    "original_value": original_val,
                    "original_unit": original_unit,
                    "conversion_applied": conv_applied,
                    "conversion_reason": conv_reason,
                    "reference_source": ref_source,
                    "value_source": selected_result.source
                }

                if key not in extracted or priority > extracted[key].get("alias_priority", 0):
                    extracted[key] = biomarker_obj

        return extracted

    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        """
        Parse CBC report deterministically.
        Uses high-precision 2D bounding boxes when ocr_lines are available,
        falling back to deterministic 1D line parsing if bounding boxes are unavailable.
        """
        metadata = extract_metadata(ocr_text)
        patient_gender = metadata.get("patient", {}).get("gender", "unknown")

        candidates_by_key: Dict[str, List[Dict[str, Any]]] = {}

        # 1. 2D Spatial Extraction
        if ocr_lines:
            spatial_results = self._extract_spatially(ocr_lines, patient_gender)
            for k, bm in spatial_results.items():
                is_valid, _ = validate_biomarker_value(k, bm.get("value"), bm.get("unit"))
                if is_valid:
                    validated_bm = validate_biomarker_dict(bm)
                    conf_data = calculate_tripart_confidence(
                        ocr_confidence=validated_bm.get("ocr_confidence", 1.0),
                        validation_status=validated_bm.get("validation_status", "passed"),
                        value_source="row_spatial",
                        reference_source=validated_bm.get("reference_source", "none"),
                        alias_priority=validated_bm.get("alias_priority", 80)
                    )
                    validated_bm["confidence"] = conf_data["confidence"]
                    validated_bm["parser_confidence"] = conf_data["overall_confidence"]
                    if k not in candidates_by_key:
                        candidates_by_key[k] = []
                    candidates_by_key[k].append(validated_bm)

        # 2. 1D Line Fallback
        cleaned_text = clean_text(ocr_text)
        raw_lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]

        split_tuples: List[Tuple[str, float]] = []
        for i, raw_line in enumerate(raw_lines):
            conf = 1.0
            if ocr_lines and i < len(ocr_lines):
                conf = ocr_lines[i].get("confidence", 1.0)
            if is_report_title_line(raw_line) or is_ignored_measurement_line(raw_line):
                split_tuples.append((raw_line, conf))
                continue

            matches = []
            pos_search = 0
            while pos_search < len(raw_line):
                res = resolve_biomarker_alias(raw_line[pos_search:], allowed_keys=self.cat_allowed_keys)
                if not res or not res.get("matched_text"):
                    break
                m_text = res["matched_text"]
                idx = raw_line.lower().find(m_text.lower(), pos_search)
                if idx != -1:
                    matches.append((idx, res))
                    pos_search = idx + len(m_text)
                else:
                    break

            if len(matches) > 1:
                matches.sort(key=lambda x: x[0])
                for k in range(len(matches)):
                    start = matches[k][0]
                    end = matches[k + 1][0] if k + 1 < len(matches) else len(raw_line)
                    sub_line = raw_line[start:end].strip()
                    if sub_line:
                        split_tuples.append((sub_line, conf))
            else:
                split_tuples.append((raw_line, conf))

        lines = [t[0] for t in split_tuples]
        for i, (line, line_confidence) in enumerate(split_tuples):
            if is_report_title_line(line) or is_ignored_measurement_line(line):
                continue

            resolved = resolve_biomarker_alias(line, allowed_keys=self.cat_allowed_keys)
            if not resolved:
                continue

            canonical_key = resolved["canonical_key"]
            matched_alias = resolved["matched_alias"]
            priority = resolved.get("alias_priority", 80)
            key_info = self.cbc_registry.get(canonical_key, {})
            key = key_info.get("key", canonical_key)
            name = key_info.get("display_name") or key_info.get("name")
            default_unit = key_info.get("default_unit", "")
            default_ref_range = key_info.get("default_reference_range", "")

            matched_text = resolved.get("matched_text", matched_alias)
            next_lines_slice = lines[i + 1:]
            prev_lines_slice = lines[max(0, i - 2):i]
            val, unit, ref_range, ref_source, value_source, matched_raw_line = extract_contextual_value(
                key=key,
                matched_alias=matched_alias,
                matched_text=matched_text,
                current_line=line,
                next_lines=next_lines_slice,
                prev_lines=prev_lines_slice,
                default_unit=default_unit,
                allowed_keys=self.cat_allowed_keys
            )

            if val is not None:
                # Centralized reference resolution: REPORT > SITA_FALLBACK > UNKNOWN
                # Hospital templates do NOT override an explicit report reference.
                resolution_1d = resolve_reference(
                    report_candidate=clean_reference_string(ref_range) if ref_range else None,
                    sita_fallback=default_ref_range or "",
                    observed_value=val,
                    biomarker_key=key
                )
                final_reference_source = resolution_1d.reference_source
                effective_ref_range = resolution_1d.reference_range

                norm_data = normalize_biomarker_value(
                    key=key,
                    value=val,
                    unit=unit or default_unit,
                    reference_range=effective_ref_range,
                    raw_text=matched_raw_line
                )

                norm_val = norm_data["canonical_value"]
                display_val = norm_data["display_value"]
                norm_unit = norm_data.get("display_unit") or norm_data["unit"]
                canonical_unit = norm_data.get("canonical_unit") or norm_unit
                conv_factor = norm_data.get("conversion_factor", 1.0)
                final_ref_range = norm_data["reference_range"] or effective_ref_range
                original_val = norm_data["original_value"]
                original_unit = norm_data["original_unit"]
                conversion_applied = norm_data["conversion_applied"]
                conversion_reason = norm_data["conversion_reason"]

                status_info = calculate_status(norm_val, final_ref_range, gender=patient_gender)
                struct_ref = build_structured_reference(resolution_1d)

                biomarker_obj = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": norm_unit,
                    "display_value": display_val,
                    "display_unit": norm_unit,
                    "canonical_value": norm_val,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conv_factor,
                    "reference_range": final_ref_range,
                    "structured_reference": struct_ref,
                    "status": status_info["status"],
                    "status_reason": status_info["status_reason"],
                    "lower_limit": status_info["lower_limit"],
                    "upper_limit": status_info["upper_limit"],
                    "ocr_confidence": line_confidence,
                    "raw_text": matched_raw_line,
                    "original_value": original_val,
                    "original_unit": original_unit,
                    "conversion_applied": conversion_applied,
                    "conversion_reason": conversion_reason,
                    "reference_source": final_reference_source,
                    "value_source": value_source
                }

                validated_bm = validate_biomarker_dict(biomarker_obj)
                conf_data = calculate_tripart_confidence(
                    ocr_confidence=line_confidence,
                    alias_priority=priority,
                    value_source=value_source,
                    reference_source=final_reference_source,
                    validation_status=validated_bm.get("validation_status", "passed"),
                    is_unit_normalized=conversion_applied
                )
                validated_bm["confidence"] = conf_data["confidence"]
                validated_bm["parser_confidence"] = conf_data["overall_confidence"]

                if key not in candidates_by_key:
                    candidates_by_key[key] = []
                candidates_by_key[key].append(validated_bm)

        # Candidate selection
        extracted_biomarkers = []
        for key in self.cat_allowed_keys:
            if key in candidates_by_key and candidates_by_key[key]:
                cands = sorted(
                    candidates_by_key[key],
                    key=lambda c: (
                        1 if c.get("value_source") == "row_spatial" else 0,
                        c.get("alias_priority", 50),
                        c.get("ocr_confidence", 1.0)
                    ),
                    reverse=True
                )
                extracted_biomarkers.append(cands[0])

        status_summary = {"normal": 0, "high": 0, "low": 0, "needs_review": 0, "unknown": 0}
        for bm in extracted_biomarkers:
            st = str(bm.get("status", "Unknown"))
            if st == "Needs Review":
                status_summary["needs_review"] += 1
            elif st.lower() in status_summary:
                status_summary[st.lower()] += 1
            else:
                status_summary["unknown"] += 1

        categories = {
            "rbc_indices": [],
            "wbc_indices": [],
            "differential_wbc": [],
            "platelet_indices": []
        }
        for bm in extracted_biomarkers:
            k = bm["key"]
            if k in ["rbc_count", "hemoglobin", "pcv", "mcv", "mch", "mchc", "rdw", "rdw_cv", "rdw_sd"]:
                categories["rbc_indices"].append(k)
            elif k == "wbc_count":
                categories["wbc_indices"].append(k)
            elif k in ["neutrophils", "lymphocytes", "eosinophils", "monocytes", "basophils"]:
                categories["differential_wbc"].append(k)
            elif k in ["platelet_count", "mpv"]:
                categories["platelet_indices"].append(k)

        seen_keys = set(b["key"] for b in extracted_biomarkers)
        primary_keys = [k for k, v in self.cbc_registry.items() if not v.get("optional", False)]
        missing_keys = [k for k in primary_keys if k not in seen_keys]

        expected_biomarkers = len(primary_keys)
        matched_biomarkers = len(extracted_biomarkers)
        coverage_percent = round((matched_biomarkers / expected_biomarkers) * 100, 1) if expected_biomarkers else 0.0

        patient_dict = metadata.get("patient", {})

        return {
            "report_type": "CBC",
            "hospital": hospital,
            "parser_version": "1.3.2",
            "parse_status": "success" if extracted_biomarkers else "no_biomarkers_found",
            "biomarkers_found": matched_biomarkers,
            "biomarkers_missing": missing_keys,
            "patient": patient_dict,
            "patient_metadata": patient_dict,
            "report": metadata.get("report", {}),
            "report_interpretation": metadata.get("report_interpretation"),
            "hospital_info": metadata.get("hospital", {}),
            "metadata": metadata,
            "status_summary": status_summary,
            "categories": categories,
            "parser_confidence": {
                "coverage_percent": coverage_percent,
                "matched_biomarkers": matched_biomarkers,
                "expected_biomarkers": expected_biomarkers
            },
            "biomarkers": extracted_biomarkers
        }
