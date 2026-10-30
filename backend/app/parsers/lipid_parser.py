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
from app.utils.lipid_registry import LIPID_BIOMARKERS
from app.utils.metadata_extractor import extract_metadata
from app.utils.reference_resolver import resolve_reference, build_structured_reference, clean_reference_string
from app.utils.ocr_noise_filter import (
    is_metadata_line,
    is_report_title_line,
    clean_line_from_metadata,
    validate_biomarker_value
)

logger = logging.getLogger(__name__)

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
    "investigation"
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


def extract_contextual_value(
    key: str,
    matched_alias: str,
    matched_text: str,
    current_line: str,
    next_lines: List[str],
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
                if pos != -1:
                    # Ignore if the matched short alias (e.g. 'mg') is part of a unit like 'mg/dL'
                    after = remainder_text[pos:]
                    if re.match(r'(?i)\bmg\s*/\s*d[lL]\b', after):
                        continue
                    if pos < next_alias_pos:
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
                # Safety check: if the line immediately following this candidate is a biomarker anchor,
                # then this numeric token belongs to that subsequent biomarker and should not be stolen.
                is_stolen = False
                if allowed_keys:
                    remaining_after_candidate = next_lines[offset:]
                    for future_line in remaining_after_candidate[:2]:
                        if is_ignored_measurement_line(future_line) or is_report_title_line(future_line):
                            continue
                        future_match = resolve_biomarker_alias(future_line, allowed_keys=allowed_keys)
                        if future_match:
                            future_key = future_match.get("canonical_key")
                            if future_key and future_key != key:
                                future_clean = clean_line_from_metadata(future_line)
                                f_val, _, _, _ = parse_line_components(future_clean, default_unit="")
                                if f_val is None:
                                    is_stolen = True
                        break

                if not is_stolen:
                    is_valid, _ = validate_biomarker_value(key, next_val, next_unit or unit)
                    if is_valid:
                        val = next_val
                        value_source = "next_line"
            if next_unit and not unit:
                unit = next_unit
            if next_ref and not ref_range:
                ref_range = next_ref
                ref_source = next_src
            matched_raw_line = f"{matched_raw_line} {next_line}"
            if val is not None:
                break

    return val, unit, ref_range, ref_source, value_source, matched_raw_line


class LipidParser(BaseParser):
    """
    Robust 2D spatial & 1D fallback Lipid Profile parser.
    Integrates spatial column alignment, biological bounds validation,
    reference range preservation, and deterministic status evaluation.
    """

    def __init__(self):
        self.lipid_registry = LIPID_BIOMARKERS
        self.cat_allowed_keys = list(LIPID_BIOMARKERS.keys())

    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        metadata = extract_metadata(ocr_text)
        patient_gender = metadata.get("patient", {}).get("gender")

        # 1. Spatial 2D extraction if bounding box lines are provided
        if ocr_lines and len(ocr_lines) > 0 and any("bbox" in l for l in ocr_lines):
            return self._parse_spatial(ocr_text, ocr_lines, hospital, metadata, patient_gender)

        # 2. 1D Fallback parsing
        return self._parse_1d(ocr_text, hospital, metadata, patient_gender)

    def _parse_spatial(
        self,
        ocr_text: str,
        ocr_lines: List[Dict[str, Any]],
        hospital: str,
        metadata: Dict[str, Any],
        patient_gender: Optional[str]
    ) -> Dict[str, Any]:
        tokens: List[Dict[str, Any]] = []
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

        # Locate table header boundaries if present
        header_result_x = None
        header_ref_x = None
        for t in tokens:
            t_lower = t["text"].lower()
            if any(w in t_lower for w in ["thanks", "dr.", "patient", "doctor", "hospital", "department", "clinical", "sample", "page", "advice", "comment"]):
                continue
            if ("observed" in t_lower or "result" in t_lower or "value" in t_lower) and "reference" not in t_lower:
                if header_result_x is None:
                    header_result_x = t["x_min"]
            if "reference" in t_lower or "interval" in t_lower or "biological" in t_lower:
                if header_ref_x is None:
                    header_ref_x = t["x_min"]

        # Detect biomarker anchors
        matched_anchors: List[Tuple[Dict[str, Any], str, str, int, str]] = []
        for t in tokens:
            text = t["text"]
            if is_report_title_line(text) or is_ignored_measurement_line(text):
                continue
            resolved = resolve_biomarker_alias(text, allowed_keys=self.cat_allowed_keys)
            if resolved:
                canonical_key = resolved["canonical_key"]
                matched_alias = resolved["matched_alias"]
                matched_text = resolved.get("matched_text", matched_alias)
                priority = resolved.get("alias_priority", 80)
                matched_anchors.append((t, canonical_key, matched_alias, priority, matched_text))

        candidates_by_key: Dict[str, List[Dict[str, Any]]] = {}

        for anchor, canonical_key, matched_alias, priority, matched_text in matched_anchors:
            key_info = self.lipid_registry.get(canonical_key, {})
            key = key_info.get("key", canonical_key)
            name = key_info.get("display_name") or key_info.get("name")
            default_unit = key_info.get("default_unit", "")
            default_ref_range = key_info.get("default_reference_range", "")

            # Identify all tokens sharing the same row (y overlap)
            row_y_center = anchor["y_center"]
            tolerance = max(10.0, anchor["height"] * 0.75)

            row_tokens = [
                tok for tok in tokens
                if abs(tok["y_center"] - row_y_center) <= tolerance
            ]
            row_tokens.sort(key=lambda tok: tok["x_min"])

            result_candidates: List[ResultCandidate] = []
            reference_candidates: List[ReferenceCandidate] = []
            unit_candidates: List[UnitCandidate] = []

            # 1. Check if anchor itself has embedded values / reference text
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
                    raw_reference=ref_same,
                    source=ref_src_same,
                    confidence=anchor["confidence"]
                ))
            if unit_same:
                unit_candidates.append(UnitCandidate(unit=unit_same, confidence=anchor["confidence"]))

            # 2. Inspect neighboring tokens on the same row
            for r_tok in row_tokens:
                if r_tok["id"] == anchor["id"]:
                    continue

                r_text = r_tok["text"].strip()
                if not r_text:
                    continue

                # Check if r_tok contains a reference range
                has_gender_keyword = any(k in r_text.lower() for k in ["male", "female", "mele", "msle"])
                ref_str, ref_src = extract_reference_range(r_text)
                is_ref_token = bool(ref_str) or has_gender_keyword or any(k in r_text.lower() for k in ["<", ">", "≥", "? 90", "5-40", "100-220", "60-130", "0.35-1.0"])

                if is_ref_token:
                    effective_ref = r_text if has_gender_keyword else (ref_str or r_text)
                    reference_candidates.append(ReferenceCandidate(
                        raw_reference=effective_ref,
                        source="report",
                        confidence=r_tok["confidence"]
                    ))

                # Extract unit
                u_str = extract_unit(r_text)
                if u_str:
                    unit_candidates.append(UnitCandidate(unit=u_str, confidence=r_tok["confidence"]))

                # Numeric extraction: ONLY if this token is NOT a reference token
                # and NOT to the right of known reference column
                is_right_of_ref = (header_ref_x is not None and r_tok["x_min"] >= header_ref_x - 10)
                if not is_ref_token and not is_right_of_ref:
                    v, _, _, _ = parse_line_components(r_text, default_unit="")
                    if v is not None:
                        is_valid, _ = validate_biomarker_value(key, v, default_unit)
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

            # Filter rejected reference numbers
            rejected_numbers = []
            for ref_c in reference_candidates:
                found_nums = re.findall(r'\d+(?:\.\d+)?', ref_c.raw_reference)
                rejected_numbers.extend([float(fn) for fn in found_nums])

            valid_result_candidates = [
                rc for rc in result_candidates
                if not (rc.source == "row_spatial" and rc.value in rejected_numbers and rc.value > 10)
            ]

            selected_result: Optional[ResultCandidate] = None
            if valid_result_candidates:
                # Prefer tokens closest to result column or same-line anchor
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
            report_ref_candidate = None
            if reference_candidates:
                report_ref_candidate = clean_reference_string(reference_candidates[0].raw_reference)
            elif ref_same:
                report_ref_candidate = clean_reference_string(ref_same)

            resolution = resolve_reference(
                report_candidate=report_ref_candidate,
                sita_fallback=default_ref_range or "",
                biomarker_key=key
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
                norm_val = norm_data["value"]
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
                    "display_unit": norm_unit,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conv_factor,
                    "reference_range": final_ref_range,
                    "structured_reference": struct_ref,
                    "status": status,
                    "status_reason": status_reason,
                    "lower_limit": lower_limit,
                    "upper_limit": upper_limit,
                    "ocr_confidence": round(selected_result.confidence, 4),
                    "parser_confidence": round(selected_result.confidence * 0.95, 4),
                    "raw_text": f"{anchor['text']} {selected_result.raw_text}",
                    "original_value": original_val,
                    "original_unit": original_unit,
                    "conversion_applied": conv_applied,
                    "conversion_reason": conv_reason,
                    "reference_source": ref_source,
                    "value_source": selected_result.source,
                    "value_validation": "passed",
                    "context_match": True,
                    "group": key_info.get("group", "cholesterol")
                }

                # Validate bounds
                validated_bm = validate_biomarker_dict(biomarker_obj)

                if key not in candidates_by_key:
                    candidates_by_key[key] = []
                candidates_by_key[key].append(validated_bm)

        # Select best candidate per key
        final_biomarkers: List[Dict[str, Any]] = []
        for k in self.cat_allowed_keys:
            if k in candidates_by_key:
                cands = candidates_by_key[k]
                cands.sort(key=lambda b: (-b.get("alias_priority", 0), -b.get("ocr_confidence", 0)))
                final_biomarkers.append(cands[0])

        return self._format_response(final_biomarkers, hospital, metadata)

    def _parse_1d(
        self,
        ocr_text: str,
        hospital: str,
        metadata: Dict[str, Any],
        patient_gender: Optional[str]
    ) -> Dict[str, Any]:
        candidates_by_key: Dict[str, List[Dict[str, Any]]] = {}
        lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            if is_report_title_line(line) or is_ignored_measurement_line(line):
                continue

            resolved = resolve_biomarker_alias(line, allowed_keys=self.cat_allowed_keys)
            if resolved:
                canonical_key = resolved["canonical_key"]
                matched_alias = resolved["matched_alias"]
                matched_text = resolved.get("matched_text", matched_alias)
                priority = resolved.get("alias_priority", 80)

                key_info = self.lipid_registry.get(canonical_key, {})
                key = key_info.get("key", canonical_key)
                name = key_info.get("display_name") or key_info.get("name")
                default_unit = key_info.get("default_unit", "")
                default_ref_range = key_info.get("default_reference_range", "")

                val, unit, ref_range, ref_source, value_source, matched_raw_line = extract_contextual_value(
                    key=key,
                    matched_alias=matched_alias,
                    matched_text=matched_text,
                    current_line=line,
                    next_lines=lines[i + 1:],
                    default_unit=default_unit,
                    allowed_keys=self.cat_allowed_keys
                )

                if val is None:
                    continue

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
                norm_val = norm_data["value"]
                norm_unit = norm_data.get("display_unit") or norm_data["unit"]
                canonical_unit = norm_data.get("canonical_unit") or norm_unit
                conv_factor = norm_data.get("conversion_factor", 1.0)
                final_ref_range = norm_data.get("reference_range") or effective_ref_range
                original_val = norm_data.get("original_value", val)
                original_unit = norm_data.get("original_unit", unit or default_unit)
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

                struct_ref = build_structured_reference(resolution_1d)

                biomarker_obj = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": norm_unit,
                    "display_unit": norm_unit,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conv_factor,
                    "reference_range": final_ref_range,
                    "structured_reference": struct_ref,
                    "status": status,
                    "status_reason": status_reason,
                    "lower_limit": lower_limit,
                    "upper_limit": upper_limit,
                    "ocr_confidence": 0.90,
                    "parser_confidence": 0.85,
                    "raw_text": matched_raw_line,
                    "original_value": original_val,
                    "original_unit": original_unit,
                    "conversion_applied": conv_applied,
                    "conversion_reason": conv_reason,
                    "reference_source": final_reference_source,
                    "value_source": value_source,
                    "value_validation": "passed",
                    "context_match": True,
                    "group": key_info.get("group", "cholesterol")
                }

                validated_bm = validate_biomarker_dict(biomarker_obj)

                if key not in candidates_by_key:
                    candidates_by_key[key] = []
                candidates_by_key[key].append(validated_bm)

        final_biomarkers: List[Dict[str, Any]] = []
        for k in self.cat_allowed_keys:
            if k in candidates_by_key:
                cands = candidates_by_key[k]
                cands.sort(key=lambda b: (-b.get("alias_priority", 0), -b.get("ocr_confidence", 0)))
                final_biomarkers.append(cands[0])

        return self._format_response(final_biomarkers, hospital, metadata)

    def _format_response(
        self,
        biomarkers: List[Dict[str, Any]],
        hospital: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        categories = {
            "cholesterol": [],
            "triglycerides": [],
            "ratios": [],
            "apolipoproteins": []
        }
        for bm in biomarkers:
            grp = bm.get("group", "cholesterol")
            if grp in categories:
                categories[grp].append(bm["key"])

        status_summary = {"normal": 0, "high": 0, "low": 0, "needs_review": 0, "unknown": 0}
        for bm in biomarkers:
            st = str(bm.get("status", "Unknown")).lower().replace(" ", "_")
            if st in status_summary:
                status_summary[st] += 1
            else:
                status_summary["unknown"] += 1

        core_keys = ["total_cholesterol", "hdl", "ldl", "vldl", "triglycerides", "non_hdl", "cholesterol_hdl_ratio"]
        extracted_keys = {bm["key"] for bm in biomarkers}
        matched_core = sum(1 for k in core_keys if k in extracted_keys)
        coverage_percent = round((matched_core / len(core_keys)) * 100, 1)

        parser_confidence = {
            "matched_biomarkers": matched_core,
            "expected_biomarkers": len(core_keys),
            "coverage_percent": coverage_percent
        }

        return {
            "report_type": "LIPID_PROFILE",
            "parser_version": "1.2.0",
            "parse_status": "success" if biomarkers else "partial",
            "hospital": hospital,
            "metadata": metadata,
            "patient_metadata": metadata.get("patient", {}),
            "report": metadata.get("report", {}),
            "report_interpretation": metadata.get("report_interpretation"),
            "hospital_info": metadata.get("hospital", {}),
            "biomarkers": biomarkers,
            "categories": categories,
            "status_summary": status_summary,
            "parser_confidence": parser_confidence,
            "summary": {
                "total_biomarkers": len(biomarkers),
                "normal": status_summary["normal"],
                "high": status_summary["high"],
                "low": status_summary["low"],
                "needs_review": status_summary["needs_review"],
                "unknown": status_summary["unknown"],
                "coverage_percent": coverage_percent
            }
        }
