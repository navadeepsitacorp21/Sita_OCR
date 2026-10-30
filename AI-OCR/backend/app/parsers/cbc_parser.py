import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from app.parsers.base_parser import BaseParser
from app.utils.text_utils import clean_text, parse_line_components
from app.utils.unit_normalizer import normalize_biomarker_value
from app.utils.alias_resolver import resolve_biomarker_alias
from app.services.status_engine import calculate_status
from app.utils.validator import validate_biomarker_dict
from app.utils.confidence import calculate_tripart_confidence
from app.utils.ocr_noise_filter import (
    is_metadata_line,
    is_report_title_line,
    clean_line_from_metadata,
    validate_biomarker_value
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIOMARKER_REF_PATH = os.path.join(BASE_DIR, "data", "biomarker_reference.json")
HOSPITAL_TEMPLATES_PATH = os.path.join(BASE_DIR, "data", "hospital_templates.json")

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


class CBCParser(BaseParser):
    """
    Hospital-grade deterministic CBC Parser for SITA OCR Engine v1.2.0.
    """
    def __init__(self, reference_path: str = BIOMARKER_REF_PATH):
        self.biomarkers_ref = self._load_reference(reference_path)
        self.cat_ref = [b for b in self.biomarkers_ref if b.get("category") == "CBC"]
        self.key_to_ref = {b["key"]: b for b in self.cat_ref}
        self.hospital_templates = self._load_hospital_templates()

    def _load_reference(self, path: str) -> List[Dict[str, Any]]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("biomarkers", [])
        return []

    def _load_hospital_templates(self) -> Dict[str, Any]:
        if os.path.exists(HOSPITAL_TEMPLATES_PATH):
            try:
                with open(HOSPITAL_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        cleaned_text = clean_text(ocr_text)
        raw_lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
        cat_allowed_keys = [b["key"] for b in self.cat_ref]

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
                res = resolve_biomarker_alias(line_str[pos_search:], allowed_keys=cat_allowed_keys)
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

        for i, (line, line_confidence) in enumerate(split_tuples):
            if is_report_title_line(line) or is_ignored_measurement_line(line):
                continue

            resolved = resolve_biomarker_alias(line, allowed_keys=cat_allowed_keys)
            if not resolved:
                continue

            canonical_key = resolved["canonical_key"]
            matched_alias = resolved["matched_alias"]
            alias_priority = resolved.get("alias_priority", 80)
            matched_ref = self.key_to_ref.get(canonical_key)
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
                allowed_keys=cat_allowed_keys
            )

            if val is not None:
                # Reference range priority order:
                # 1. OCR report reference range ("report")
                # 2. Hospital template reference range ("hospital_template")
                # 3. Global default fallback reference range ("fallback")
                hosp_config = self.hospital_templates.get(hospital, {})
                hosp_ref_range = hosp_config.get("reference_ranges", {}).get(key, "")

                if ref_range:
                    final_reference_source = "report"
                    effective_ref_range = ref_range
                elif hosp_ref_range:
                    final_reference_source = "hospital_template"
                    effective_ref_range = hosp_ref_range
                elif default_ref_range:
                    final_reference_source = "fallback"
                    effective_ref_range = default_ref_range
                else:
                    final_reference_source = "none"
                    effective_ref_range = ""

                norm_data = normalize_biomarker_value(
                    key=key,
                    value=val,
                    unit=unit,
                    reference_range=effective_ref_range,
                    raw_text=matched_raw_line
                )

                norm_val = norm_data["canonical_value"]
                display_val = norm_data["display_value"]
                display_unit = norm_data["display_unit"]
                display_ref_range = norm_data.get("display_reference_range") or effective_ref_range
                canonical_unit = norm_data["canonical_unit"]
                conversion_factor = norm_data.get("conversion_factor", 1.0)
                final_ref_range = norm_data["reference_range"] or effective_ref_range
                original_val = norm_data["original_value"]
                original_unit = norm_data["original_unit"]
                conversion_applied = norm_data["conversion_applied"]
                conversion_reason = norm_data["conversion_reason"]

                status_info = calculate_status(norm_val, final_ref_range)

                raw_bm_dict = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": alias_priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": canonical_unit,
                    "display_value": display_val,
                    "display_unit": display_unit,
                    "display_reference_range": display_ref_range,
                    "canonical_value": norm_val,
                    "canonical_unit": canonical_unit,
                    "conversion_factor": conversion_factor,
                    "reference_range": final_ref_range,
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

                # Validation & Confidence Calculation
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
        for ref_bm in self.cat_ref:
            k = ref_bm["key"]
            if k in candidates_by_key and candidates_by_key[k]:
                # Pick highest priority candidate
                cands = sorted(
                    candidates_by_key[k],
                    key=lambda c: (c.get("alias_priority", 50), c.get("ocr_confidence", 1.0)),
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

        all_primary_keys = [b["key"] for b in self.cat_ref]
        seen_keys = set(b["key"] for b in extracted_biomarkers)
        missing_keys = [k for k in all_primary_keys if k not in seen_keys]

        return {
            "report_type": "CBC",
            "hospital": hospital,
            "parser_version": "1.2.0",
            "parse_status": "success" if extracted_biomarkers else "no_biomarkers_found",
            "biomarkers_found": len(extracted_biomarkers),
            "biomarkers_missing": missing_keys,
            "status_summary": status_summary,
            "biomarkers": extracted_biomarkers
        }
