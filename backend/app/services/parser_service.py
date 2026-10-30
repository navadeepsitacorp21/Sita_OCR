import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from app.utils.text_utils import clean_text, parse_line_components
from app.utils.unit_normalizer import normalize_biomarker_value
from app.utils.alias_resolver import resolve_biomarker_alias
from app.services.status_engine import calculate_status
from app.services.vitamin_status_engine import (
    classify_vitamin_d_stage,
    extract_vitamin_d_interpretation_ranges
)
from app.parsers.report_detector import detect_report
from app.parsers.parser_registry import get_parser_registry

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIOMARKER_REF_PATH = os.path.join(BASE_DIR, "data", "biomarker_reference.json")

from app.utils.ocr_noise_filter import (
    is_metadata_line,
    is_report_title_line,
    clean_line_from_metadata,
    validate_biomarker_value
)

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


def calculate_biomarker_confidence(
    alias_priority: int,
    value_source: str,
    reference_source: str,
    ocr_confidence: float = 1.0
) -> float:
    score = float(ocr_confidence)
    if value_source in ["next_line", "lookahead"]:
        score -= 0.05
    if reference_source == "fallback":
        score -= 0.05
    if alias_priority < 80:
        score -= 0.05
    return max(0.50, round(score, 2))


def extract_contextual_value(
    key: str,
    matched_alias: str,
    matched_text: str,
    current_line: str,
    next_lines: List[str],
    default_unit: str = "",
    category: str = "",
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

    if key == "egfr":
        clean_egfr = re.sub(r'\b[Gg][1-5][abcABC]?\b', ' ', clean_remainder)
        val, unit, ref_range, ref_source = parse_line_components(clean_egfr, default_unit=default_unit)
    else:
        val, unit, ref_range, ref_source = parse_line_components(clean_remainder, default_unit=default_unit)

    if val is not None:
        is_valid, _ = validate_biomarker_value(key, val, unit)
        if not is_valid:
            val = None

    value_source = "same_line" if val is not None else "none"
    matched_raw_line = current_line

    max_lookahead = 3 if category == "VITAMIN_PROFILE" else 2
    if val is None and next_lines:
        for offset, next_line in enumerate(next_lines[:max_lookahead], 1):
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

            if val is not None and (category != "VITAMIN_PROFILE" or (unit and ref_range)):
                break

    if val is not None and category == "VITAMIN_PROFILE" and (not unit or not ref_range) and next_lines:
        for next_line in next_lines[:2]:
            if is_ignored_measurement_line(next_line) or is_report_title_line(next_line):
                continue
            if allowed_keys and resolve_biomarker_alias(next_line, allowed_keys=allowed_keys):
                break
            cleaned_next = clean_line_from_metadata(next_line)
            _, next_unit, next_ref, next_src = parse_line_components(cleaned_next, default_unit=default_unit)
            if next_unit and not unit:
                unit = next_unit
            if next_ref and not ref_range:
                ref_range = next_ref
                ref_source = next_src
            if unit and ref_range:
                break

    return val, unit, ref_range, ref_source, value_source, matched_raw_line


def resolve_highest_priority_candidate(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None

    def candidate_sort_key(c: Dict[str, Any]):
        alias_priority = c.get("alias_priority", 50)
        confidence = c.get("ocr_confidence", 1.0)
        same_line = 1 if c.get("value_source") == "same_line" else 0
        context_match = 1 if c.get("context_match") else 0
        return (alias_priority, confidence, same_line, context_match)

    sorted_candidates = sorted(candidates, key=candidate_sort_key, reverse=True)
    return sorted_candidates[0]


class ParserService:
    """
    SITA OCR Engine Orchestrator Parser Service v1.2.0.
    Delegates parsing execution to Document Detector and Parser Registry.
    """
    def __init__(self, reference_path: str = BIOMARKER_REF_PATH):
        self.biomarkers_ref = self._load_reference(reference_path)
        self.key_to_ref = {b["key"]: b for b in self.biomarkers_ref}

    def _load_reference(self, path: str) -> List[Dict[str, Any]]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("biomarkers", [])
        return []

    def _parse_category_report(
        self,
        category: str,
        report_type: str,
        parser_version: str,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        default_categories: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        cleaned_text = clean_text(ocr_text)
        raw_lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
        cat_ref = [b for b in self.biomarkers_ref if b.get("category") == category]
        cat_allowed_keys = [b["key"] for b in cat_ref]
        key_to_group = {b["key"]: b.get("group", "general") for b in cat_ref}

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
                category=category,
                allowed_keys=cat_allowed_keys
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
                    unit=unit,
                    reference_range=effective_ref_range,
                    raw_text=matched_raw_line
                )

                norm_val = norm_data["value"]
                norm_unit = norm_data["unit"]
                final_ref_range = norm_data["reference_range"] or effective_ref_range
                original_val = norm_data["original_value"]
                original_unit = norm_data["original_unit"]
                conversion_applied = norm_data["conversion_applied"]
                conversion_reason = norm_data["conversion_reason"]

                status_info = calculate_status(norm_val, final_ref_range)
                parser_conf = calculate_biomarker_confidence(
                    alias_priority=alias_priority,
                    value_source=value_source,
                    reference_source=final_reference_source,
                    ocr_confidence=line_confidence
                )

                biomarker_dict = {
                    "key": key,
                    "name": name,
                    "matched_alias": matched_alias,
                    "alias_priority": alias_priority,
                    "alias_source": "resolver",
                    "value": norm_val,
                    "unit": norm_unit,
                    "reference_range": final_ref_range,
                    "status": status_info["status"],
                    "status_reason": status_info["status_reason"],
                    "lower_limit": status_info["lower_limit"],
                    "upper_limit": status_info["upper_limit"],
                    "ocr_confidence": line_confidence,
                    "parser_confidence": parser_conf,
                    "raw_text": matched_raw_line,
                    "original_value": original_val,
                    "original_unit": original_unit,
                    "conversion_applied": conversion_applied,
                    "conversion_reason": conversion_reason,
                    "reference_source": final_reference_source,
                    "value_source": value_source,
                    "value_validation": "passed",
                    "context_match": True
                }

                if key == "egfr":
                    stage_match = re.search(r'\b(?:EGFR\s+CATEGORY|CKD\s+STAGE|STAGE)\s*[:\-]?\s*([Gg][1-5][abcABC]?)\b', ocr_text, re.IGNORECASE)
                    if stage_match:
                        biomarker_dict["ckd_stage"] = stage_match.group(1).upper()

                if "family" in matched_ref:
                    biomarker_dict["family"] = matched_ref["family"]
                if "is_primary" in matched_ref:
                    biomarker_dict["is_primary"] = matched_ref["is_primary"]

                if key == "vitamin_d":
                    interp_ranges = extract_vitamin_d_interpretation_ranges(ocr_text)
                    if interp_ranges:
                        biomarker_dict["clinical_ranges"] = interp_ranges
                        biomarker_dict["reference_source"] = "report"

                    stage, msg, v_status = classify_vitamin_d_stage(norm_val)
                    if stage:
                        biomarker_dict["clinical_stage"] = stage
                        biomarker_dict["clinical_message"] = msg
                        if v_status:
                            biomarker_dict["status"] = v_status

                if key not in candidates_by_key:
                    candidates_by_key[key] = []
                candidates_by_key[key].append(biomarker_dict)

        if "vitamin_d" not in candidates_by_key:
            if "vitamin_d3" in candidates_by_key:
                best_d3 = resolve_highest_priority_candidate(candidates_by_key["vitamin_d3"])
                if best_d3:
                    vit_d_ref = self.key_to_ref.get("vitamin_d", {})
                    d_fallback = dict(best_d3)
                    d_fallback["key"] = "vitamin_d"
                    d_fallback["name"] = vit_d_ref.get("display_name") or vit_d_ref.get("name", "Vitamin D Total")
                    d_fallback["alias_priority"] = 50
                    d_fallback["family"] = vit_d_ref.get("family", "vitamin_d_family")
                    d_fallback["is_primary"] = True
                    stage, msg, v_status = classify_vitamin_d_stage(d_fallback.get("value"))
                    if stage:
                        d_fallback["clinical_stage"] = stage
                        d_fallback["clinical_message"] = msg
                        if v_status:
                            d_fallback["status"] = v_status
                    candidates_by_key["vitamin_d"] = [d_fallback]
            elif "vitamin_d2" in candidates_by_key:
                best_d2 = resolve_highest_priority_candidate(candidates_by_key["vitamin_d2"])
                if best_d2:
                    vit_d_ref = self.key_to_ref.get("vitamin_d", {})
                    d_fallback = dict(best_d2)
                    d_fallback["key"] = "vitamin_d"
                    d_fallback["name"] = vit_d_ref.get("display_name") or vit_d_ref.get("name", "Vitamin D Total")
                    d_fallback["alias_priority"] = 40
                    d_fallback["family"] = vit_d_ref.get("family", "vitamin_d_family")
                    d_fallback["is_primary"] = True
                    stage, msg, v_status = classify_vitamin_d_stage(d_fallback.get("value"))
                    if stage:
                        d_fallback["clinical_stage"] = stage
                        d_fallback["clinical_message"] = msg
                        if v_status:
                            d_fallback["status"] = v_status
                    candidates_by_key["vitamin_d"] = [d_fallback]

        resolved_by_key: Dict[str, Dict[str, Any]] = {}
        for key, candidate_list in candidates_by_key.items():
            best_cand = resolve_highest_priority_candidate(candidate_list)
            if best_cand:
                resolved_by_key[key] = best_cand

        extracted_biomarkers = []
        seen_keys = set(resolved_by_key.keys())
        for ref_bm in cat_ref:
            k = ref_bm["key"]
            if k in resolved_by_key:
                extracted_biomarkers.append(resolved_by_key[k])

        categories = {}
        if default_categories is not None:
            categories = {cat_name: [] for cat_name in default_categories.keys()}
        for bm in extracted_biomarkers:
            grp = key_to_group.get(bm["key"], "general")
            if grp in categories:
                categories[grp].append(bm["key"])
            elif default_categories is None:
                categories.setdefault(grp, []).append(bm["key"])

        status_summary = {"normal": 0, "high": 0, "low": 0, "unknown": 0}
        for bm in extracted_biomarkers:
            st = str(bm.get("status", "Unknown")).lower()
            if st in status_summary:
                status_summary[st] += 1
            else:
                status_summary["unknown"] += 1

        primary_cat_ref = [b for b in cat_ref if not b.get("optional", False)]
        all_primary_keys = [b["key"] for b in primary_cat_ref]
        missing_keys = [k for k in all_primary_keys if k not in seen_keys]

        expected_biomarkers = len(primary_cat_ref)
        matched_biomarkers = len(extracted_biomarkers)
        primary_matched_biomarkers = sum(1 for k in seen_keys if k in all_primary_keys)
        coverage_percent = round((primary_matched_biomarkers / expected_biomarkers) * 100, 1) if expected_biomarkers else 0

        parser_confidence = {
            "coverage_percent": min(100.0, coverage_percent),
            "matched_biomarkers": matched_biomarkers,
            "expected_biomarkers": expected_biomarkers
        }

        res = {
            "report_type": report_type,
            "parser_version": parser_version,
            "parse_status": "success" if extracted_biomarkers else "no_biomarkers_found",
            "biomarkers_found": matched_biomarkers,
            "biomarkers_missing": missing_keys,
            "status_summary": status_summary,
            "biomarkers": extracted_biomarkers
        }

        if default_categories is not None:
            res["categories"] = categories
            res["parser_confidence"] = parser_confidence

        return res

    def parse_cbc_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        hospital = detected["hospital"]
        registry = get_parser_registry()
        parser = registry.get_parser("CBC", hospital=hospital)
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=hospital)

    def parse_lipid_profile_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        registry = get_parser_registry()
        parser = registry.get_parser("LIPID_PROFILE", hospital=detected["hospital"])
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=detected["hospital"])

    def parse_diabetes_profile_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        registry = get_parser_registry()
        parser = registry.get_parser("DIABETES_PROFILE", hospital=detected["hospital"])
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=detected["hospital"])

    def parse_thyroid_profile_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        registry = get_parser_registry()
        parser = registry.get_parser("THYROID_PROFILE", hospital=detected["hospital"])
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=detected["hospital"])

    def parse_liver_function_test_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        registry = get_parser_registry()
        parser = registry.get_parser("LIVER_FUNCTION_TEST", hospital=detected["hospital"])
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=detected["hospital"])

    def parse_kidney_function_test_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        registry = get_parser_registry()
        parser = registry.get_parser("KIDNEY_FUNCTION_TEST", hospital=detected["hospital"])
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=detected["hospital"])

    def parse_vitamin_profile_report(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        detected = detect_report(ocr_text)
        registry = get_parser_registry()
        parser = registry.get_parser("VITAMIN_PROFILE", hospital=detected["hospital"])
        return parser.parse(ocr_text, ocr_lines=ocr_lines, hospital=detected["hospital"])


# Singleton parser instance
parser_service = ParserService()


def parse_cbc_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_cbc_report(ocr_text, ocr_lines=ocr_lines)


def parse_lipid_profile_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_lipid_profile_report(ocr_text, ocr_lines=ocr_lines)


def parse_diabetes_profile_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_diabetes_profile_report(ocr_text, ocr_lines=ocr_lines)


def parse_thyroid_profile_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_thyroid_profile_report(ocr_text, ocr_lines=ocr_lines)


def parse_liver_function_test_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_liver_function_test_report(ocr_text, ocr_lines=ocr_lines)


def parse_kidney_function_test_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_kidney_function_test_report(ocr_text, ocr_lines=ocr_lines)


def parse_vitamin_profile_report(
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    return parser_service.parse_vitamin_profile_report(ocr_text, ocr_lines=ocr_lines)
