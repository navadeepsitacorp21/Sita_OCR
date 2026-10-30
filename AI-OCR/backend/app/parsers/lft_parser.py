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
from app.utils.lft_registry import LFT_BIOMARKERS
from app.utils.metadata_extractor import extract_metadata
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
    "stage",
    "grade",
    "reference note",
    "clinical note",
    "method"
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
                # Safety check: if the line immediately following this candidate is a biomarker anchor,
                # then this numeric token belongs to that subsequent biomarker and should not be stolen.
                rem_lines = next_lines[offset:]
                if rem_lines and allowed_keys and resolve_biomarker_alias(rem_lines[0], allowed_keys=allowed_keys):
                    # Do not steal next_val as it belongs to the following biomarker
                    pass
                else:
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


class LFTParser(BaseParser):
    """
    Hospital-grade deterministic Liver Function Test (LFT) Parser for SITA OCR Engine v1.3.2.
    Parses all 12 canonical LFT biomarkers, performs spatial row-aware extraction,
    guarantees ResultCandidate > ReferenceCandidate separation, and extracts patient metadata.
    """
    def __init__(self):
        self.lft_registry = LFT_BIOMARKERS
        self.cat_allowed_keys = list(LFT_BIOMARKERS.keys())

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

        # Enrich tokens with geometry
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

        # Locate table header boundaries if present
        header_result_x = None
        header_ref_x = None
        for t in tokens:
            t_lower = t["text"].lower()
            if "observed" in t_lower or "result" in t_lower or "value" in t_lower:
                header_result_x = t["x_min"]
            if "reference" in t_lower or "interval" in t_lower or "biological" in t_lower:
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

        for anchor, canonical_key, matched_alias, priority, matched_text in matched_anchors:
            key_info = self.lft_registry.get(canonical_key, {})
            key = key_info.get("key", canonical_key)
            name = key_info.get("display_name") or key_info.get("name")
            default_unit = key_info.get("default_unit", "")
            default_ref_range = key_info.get("default_reference_range", "")

            # Identify all tokens sharing the same row (y overlap)
            row_y_center = anchor["y_center"]
            tolerance = anchor["height"] * 0.75

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
                ref_str, ref_src = extract_reference_range(r_text)
                is_ref_token = bool(ref_str) or any(k in r_text.lower() for k in ["male", "female", "<", ">"])

                if is_ref_token:
                    effective_ref = ref_str or r_text
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

            # Debug candidate tracing
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"BIOMARKER: {key}")
                logger.debug(f"ROW_Y: {row_y_center}")
                logger.debug(f"RESULT CANDIDATES: {[(rc.value, rc.source, rc.x_pos) for rc in result_candidates]}")
                logger.debug(f"REFERENCE CANDIDATES: {[rc.raw_reference for rc in reference_candidates]}")

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

            # Resolve Reference Range
            final_ref_range = ""
            final_ref_source = "none"
            if reference_candidates:
                final_ref_range = reference_candidates[0].raw_reference
                final_ref_source = "report"
            elif default_ref_range:
                final_ref_range = default_ref_range
                final_ref_source = "fallback"

            if selected_result is not None:
                norm_data = normalize_biomarker_value(
                    key=key,
                    value=selected_result.value,
                    unit=final_unit,
                    reference_range=final_ref_range,
                    raw_text=selected_result.raw_text
                )

                norm_val = norm_data["value"]
                display_unit = norm_data.get("display_unit") or norm_data["unit"]
                canonical_unit = norm_data.get("canonical_unit") or display_unit
                conversion_factor = norm_data.get("conversion_factor", 1.0)
                final_ref_range = norm_data["reference_range"] or final_ref_range
                original_val = norm_data["original_value"]
                original_unit = norm_data["original_unit"]
                conversion_applied = norm_data["conversion_applied"]
                conversion_reason = norm_data["conversion_reason"]

                status_info = calculate_status(norm_val, final_ref_range, gender=patient_gender)
                structured_ref = parse_structured_reference_range(final_ref_range)

                raw_bm_dict = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": display_unit,
                    "display_unit": display_unit,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conversion_factor,
                    "reference_range": final_ref_range,
                    "structured_reference": structured_ref,
                    "status": status_info["status"],
                    "status_reason": status_info["status_reason"],
                    "lower_limit": status_info["lower_limit"],
                    "upper_limit": status_info["upper_limit"],
                    "ocr_confidence": selected_result.confidence,
                    "raw_text": selected_result.raw_text,
                    "original_value": original_val,
                    "original_unit": original_unit,
                    "conversion_applied": conversion_applied,
                    "conversion_reason": conversion_reason,
                    "reference_source": final_ref_source,
                    "value_source": "row_spatial" if selected_result.source == "row_spatial" else "same_line"
                }

                validated_bm = validate_biomarker_dict(raw_bm_dict)
                conf_data = calculate_tripart_confidence(
                    ocr_confidence=selected_result.confidence,
                    alias_priority=priority,
                    value_source=validated_bm["value_source"],
                    reference_source=final_ref_source,
                    validation_status=validated_bm.get("validation_status", "passed"),
                    is_unit_normalized=conversion_applied
                )

                validated_bm["confidence"] = conf_data["confidence"]
                validated_bm["parser_confidence"] = conf_data["overall_confidence"]

                extracted[key] = validated_bm

        return extracted

    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        # Extract Patient, Report, and Hospital Metadata
        metadata = extract_metadata(ocr_text)
        patient_gender = metadata.get("patient", {}).get("gender", "unknown")

        cleaned_text = clean_text(ocr_text)
        raw_lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]

        line_tuples: List[Tuple[str, float]] = []
        for i, raw_line in enumerate(raw_lines):
            conf = 1.0
            if ocr_lines and i < len(ocr_lines):
                conf = ocr_lines[i].get("confidence", 1.0)
            line_tuples.append((raw_line, conf))

        split_tuples: List[Tuple[str, float]] = []
        for line_str, conf in line_tuples:
            if is_report_title_line(line_str) or is_ignored_measurement_line(line_str):
                split_tuples.append((line_str, conf))
                continue

            matches = []
            pos_search = 0
            while pos_search < len(line_str):
                res = resolve_biomarker_alias(line_str[pos_search:], allowed_keys=self.cat_allowed_keys)
                if not res or not res.get("matched_text"):
                    break
                m_text = res["matched_text"]
                idx = line_str.lower().find(m_text.lower(), pos_search)
                if idx != -1:
                    matches.append((idx, res))
                    pos_search = idx + len(m_text)
                else:
                    break

            if len(matches) > 1:
                matches.sort(key=lambda x: x[0])
                for k in range(len(matches)):
                    start = matches[k][0]
                    end = matches[k + 1][0] if k + 1 < len(matches) else len(line_str)
                    sub_line = line_str[start:end].strip()
                    if sub_line:
                        split_tuples.append((sub_line, conf))
            else:
                split_tuples.append((line_str, conf))

        lines = [t[0] for t in split_tuples]
        candidates_by_key: Dict[str, List[Dict[str, Any]]] = {}

        # 1. Attempt spatial row-aware extraction if ocr_lines geometry is provided
        if ocr_lines:
            spatial_results = self._extract_spatially(ocr_lines, patient_gender)
            for k, bm in spatial_results.items():
                if k not in candidates_by_key:
                    candidates_by_key[k] = []
                candidates_by_key[k].append(bm)

        # 2. Contextual line-based extraction
        for i, (line, line_confidence) in enumerate(split_tuples):
            if is_report_title_line(line) or is_ignored_measurement_line(line):
                continue

            resolved = resolve_biomarker_alias(line, allowed_keys=self.cat_allowed_keys)
            if not resolved:
                continue

            canonical_key = resolved["canonical_key"]
            matched_alias = resolved["matched_alias"]
            alias_priority = resolved.get("alias_priority", 80)
            matched_ref = self.lft_registry.get(canonical_key)
            if not matched_ref:
                continue

            key = matched_ref["key"]
            name = matched_ref.get("display_name") or matched_ref.get("name")
            default_unit = matched_ref.get("default_unit", "")
            default_ref_range = matched_ref.get("default_reference_range", "")

            matched_text = resolved.get("matched_text", matched_alias)
            next_lines_slice = lines[i + 1:]
            val, unit, ref_range, ref_source, value_source, matched_raw_line = extract_contextual_value(
                key=key,
                matched_alias=matched_alias,
                matched_text=matched_text,
                current_line=line,
                next_lines=next_lines_slice,
                default_unit=default_unit,
                allowed_keys=self.cat_allowed_keys
            )

            if val is not None:
                if ref_range:
                    final_reference_source = "report"
                    effective_ref_range = ref_range
                elif default_ref_range:
                    final_reference_source = "fallback"
                    effective_ref_range = default_ref_range
                else:
                    final_reference_source = "none"
                    effective_ref_range = ""

                norm_data = normalize_biomarker_value(
                    key=key,
                    value=val,
                    unit=unit or default_unit,
                    reference_range=effective_ref_range,
                    raw_text=matched_raw_line
                )

                norm_val = norm_data["value"]
                display_unit = norm_data.get("display_unit") or norm_data["unit"]
                canonical_unit = norm_data.get("canonical_unit") or display_unit
                conversion_factor = norm_data.get("conversion_factor", 1.0)
                final_ref_range = norm_data["reference_range"] or effective_ref_range
                original_val = norm_data["original_value"]
                original_unit = norm_data["original_unit"]
                conversion_applied = norm_data["conversion_applied"]
                conversion_reason = norm_data["conversion_reason"]

                # Evaluate status using gender-aware logic
                status_info = calculate_status(norm_val, final_ref_range, gender=patient_gender)
                structured_ref = parse_structured_reference_range(final_ref_range)

                raw_bm_dict = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": alias_priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": display_unit,
                    "display_unit": display_unit,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conversion_factor,
                    "reference_range": final_ref_range,
                    "structured_reference": structured_ref,
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

                validated_bm = validate_biomarker_dict(raw_bm_dict)
                conf_data = calculate_tripart_confidence(
                    ocr_confidence=line_confidence,
                    alias_priority=alias_priority,
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

        extracted_biomarkers = []
        for key in self.cat_allowed_keys:
            if key in candidates_by_key and candidates_by_key[key]:
                # Spatial extraction takes priority when available
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
            "liver_enzymes": [],
            "bilirubin": [],
            "proteins": [],
            "ratios": []
        }
        for bm in extracted_biomarkers:
            k = bm["key"]
            group = self.lft_registry.get(k, {}).get("group", "general")
            if group in categories:
                categories[group].append(k)

        seen_keys = set(b["key"] for b in extracted_biomarkers)
        missing_keys = [k for k in self.cat_allowed_keys if k not in seen_keys]

        expected_biomarkers = len(self.cat_allowed_keys)
        matched_biomarkers = len(extracted_biomarkers)
        coverage_percent = round((matched_biomarkers / expected_biomarkers) * 100, 1) if expected_biomarkers else 0.0

        patient_dict = metadata.get("patient", {})

        return {
            "report_type": "LIVER_FUNCTION_TEST",
            "hospital": hospital,
            "parser_version": "1.3.2",
            "parse_status": "success" if extracted_biomarkers else "no_biomarkers_found",
            "biomarkers_found": matched_biomarkers,
            "biomarkers_missing": missing_keys,
            "patient": patient_dict,
            "patient_metadata": patient_dict,
            "report": metadata.get("report", {}),
            "hospital_info": metadata.get("hospital", {}),
            "status_summary": status_summary,
            "categories": categories,
            "parser_confidence": {
                "coverage_percent": coverage_percent,
                "matched_biomarkers": matched_biomarkers,
                "expected_biomarkers": expected_biomarkers
            },
            "biomarkers": extracted_biomarkers
        }
