import re
from typing import Dict, Any, Optional, Tuple


def clean_reference_range_text(text: str) -> str:
    """
    Clean and repair OCR artifacts in reference range text.
    Handles fused numbers e.g. "8.510.5" -> "8.5 - 10.5", "3.57.2" -> "3.5 - 7.2",
    "1540" -> "15 - 40", "? 90" -> ">= 90", "msle" -> "male", etc.
    """
    if not text:
        return ""
    clean = str(text).strip()
    # Strip commas in numbers
    clean = re.sub(r'\b\d{1,3}(?:,\d{2,3})+\b', lambda m: m.group(0).replace(',', ''), clean)
    # Fix male/female typo in reference ranges
    clean = re.sub(r'\bmsle\b', 'male', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bmele\b', 'male', clean, flags=re.IGNORECASE)

    # Fused decimal ranges with two dots: e.g. "8.510.5" -> "8.5 - 10.5", "3.57.2" -> "3.5 - 7.2", "0.61.1" -> "0.6 - 1.1"
    def _fix_two_dots(m):
        p1, mid, p3 = m.group(1), m.group(2), m.group(3)
        for k in range(1, len(mid)):
            d1 = mid[:k]
            i2 = mid[k:]
            try:
                n1 = float(f"{p1}.{d1}")
                n2 = float(f"{i2}.{p3}")
                if n1 < n2:
                    return f"{p1}.{d1} - {i2}.{p3}"
            except Exception:
                pass
        return m.group(0)

    clean = re.sub(r'(\d+)\.(\d+)\.(\d+)', _fix_two_dots, clean)

    # Fused integer ranges for Urea: "1540" -> "15 - 40"
    clean = re.sub(r'\b1540\b', '15 - 40', clean)
    # OCR question mark for inequality: "? 90" -> ">= 90"
    clean = re.sub(r'\?\s*(\d+)', r'>= \1', clean)
    if clean.startswith("(") and clean.endswith(")"):
        clean = clean[1:-1].strip()
    return clean


def parse_gender_specific_bounds(clean_range: str) -> Tuple[Optional[Tuple[Optional[float], Optional[float]]], Optional[Tuple[Optional[float], Optional[float]]]]:
    """
    Parse gender-specific reference range text into (male_bounds, female_bounds).
    Supports formats like:
    - "Male <45 Female <35"
    - "Male: 10-50 Female: 10-35"
    - "M:10-50 F:10-35"
    - "Male 10-50 / Female 10-35"
    """
    if not clean_range:
        return None, None

    text = clean_reference_range_text(clean_range)

    # Extract male part and female part using regex (supporting both Male <45 and Male 40)
    male_match = re.search(r'\b(?:male|m)\b\s*[:\-]?\s*([<≤>≥]=?\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:-|to|–|—)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)', text, re.IGNORECASE)
    female_match = re.search(r'\b(?:female|f)\b\s*[:\-]?\s*([<≤>≥]=?\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:-|to|–|—)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)', text, re.IGNORECASE)

    def _parse_gender_token(token: Optional[str]) -> Optional[Tuple[Optional[float], Optional[float]]]:
        if not token:
            return None
        tok_clean = token.strip()
        # If token is just a bare number e.g. "40", in reference context it represents upper limit (e.g. Male <40)
        if re.match(r'^\d+(?:\.\d+)?$', tok_clean):
            return None, float(tok_clean)
        return parse_reference_range_bounds(tok_clean)

    male_bounds = _parse_gender_token(male_match.group(1)) if male_match else None
    female_bounds = _parse_gender_token(female_match.group(1)) if female_match else None

    return male_bounds, female_bounds


def parse_reference_range_bounds(reference_range: Optional[str], gender: str = "unknown") -> Tuple[Optional[float], Optional[float]]:
    """
    Parse biological reference range string into numeric lower and upper limits.
    Supports gender-specific ranges, single bounds, and dual ranges.
    """
    if not reference_range:
        return None, None

    clean_range = clean_reference_range_text(str(reference_range))

    # Check for gender-specific ranges first
    male_bounds, female_bounds = parse_gender_specific_bounds(clean_range)
    if male_bounds or female_bounds:
        g_lower = gender.lower()
        if g_lower == "male" and male_bounds and (male_bounds[0] is not None or male_bounds[1] is not None):
            return male_bounds
        if g_lower == "female" and female_bounds and (female_bounds[0] is not None or female_bounds[1] is not None):
            return female_bounds
        
        # Fall back to overall range if gender is unknown or specific bound is missing
        all_mins = [b[0] for b in [male_bounds, female_bounds] if b and b[0] is not None]
        all_maxs = [b[1] for b in [male_bounds, female_bounds] if b and b[1] is not None]
        
        min_val = min(all_mins) if all_mins else None
        max_val = max(all_maxs) if all_maxs else None
        return min_val, max_val

    # Strip notes in parentheses like (Normal), (Norsl), (CKD-EPI)
    clean_range = re.sub(r'\s*\((?:normal|norsl|ckd-epi|generic|standard)\)', '', clean_range, flags=re.IGNORECASE).strip()

    # Pattern 1: Single upper bound e.g. "< 200", "<=200", "≤200", "< 55"
    upper_match = re.search(r'^(?:[<≤]=?)\s*(\d+(?:\.\d+)?)', clean_range, re.IGNORECASE)
    if upper_match:
        return None, float(upper_match.group(1))

    # Pattern 2: Single lower bound e.g. "> 40", ">=40", "≥40", "≥ 90", "? 90"
    lower_match = re.search(r'^(?:[>≥]=?|>=|\?=?)\s*(\d+(?:\.\d+)?)', clean_range, re.IGNORECASE)
    if lower_match:
        return float(lower_match.group(1)), None

    # Pattern 3: Dual bound range e.g. "12.5 - 16.0", "4000-10500", "12.5 to 16.0"
    range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)', clean_range, re.IGNORECASE)
    if range_match:
        val1 = float(range_match.group(1))
        val2 = float(range_match.group(2))
        return min(val1, val2), max(val1, val2)

    return None, None


def parse_structured_reference_range(reference_range: Optional[str]) -> Dict[str, Any]:
    """
    Step 3: Return structured reference range dictionary for Health Vault.
    """
    if not reference_range:
        return {"source": "none"}

    clean_range = clean_reference_range_text(str(reference_range))
    male_bounds, female_bounds = parse_gender_specific_bounds(clean_range)

    res = {"source": "report", "raw": clean_range}

    if male_bounds:
        res["male"] = {"min": male_bounds[0], "max": male_bounds[1]}
    if female_bounds:
        res["female"] = {"min": female_bounds[0], "max": female_bounds[1]}

    gen_min, gen_max = parse_reference_range_bounds(clean_range)
    res["generic"] = {"min": gen_min, "max": gen_max}

    return res


def calculate_status(
    value: Optional[float],
    reference_range: Optional[str],
    gender: str = "unknown"
) -> Dict[str, Any]:
    """
    Evaluate extracted numeric biomarker value against biological reference range.
    Supports gender-specific ranges, inclusive dual ranges, and strict/non-strict bounds.
    """
    if value is None:
        return {
            "status": "Unknown",
            "status_reason": "Value is missing or unparseable.",
            "lower_limit": None,
            "upper_limit": None
        }

    # If the reference range is gender-specific, a known patient gender (male/female) is strictly required
    clean_ref = clean_reference_range_text(str(reference_range))
    male_bounds, female_bounds = parse_gender_specific_bounds(clean_ref)
    if male_bounds or female_bounds:
        g_clean = (gender or "").strip().lower()
        if g_clean not in ("male", "female"):
            return {
                "status": "Needs Review",
                "status_reason": "Gender-specific reference range requires patient gender context.",
                "lower_limit": None,
                "upper_limit": None,
            }

    lower_limit, upper_limit = parse_reference_range_bounds(reference_range, gender=gender)

    if lower_limit is None and upper_limit is None:
        return {
            "status": "Unknown",
            "status_reason": "Reference range missing or cannot be parsed.",
            "lower_limit": None,
            "upper_limit": None
        }

    ref_str = str(reference_range).strip()
    if ref_str.startswith("(") and ref_str.endswith(")"):
        ref_str = ref_str[1:-1].strip()

    # Dual bounded range (lower_limit and upper_limit)
    if lower_limit is not None and upper_limit is not None:
        if value < lower_limit:
            return {
                "status": "Low",
                "status_reason": f"Value is below the lower biological reference limit of {lower_limit}.",
                "lower_limit": lower_limit,
                "upper_limit": upper_limit
            }
        elif value > upper_limit:
            return {
                "status": "High",
                "status_reason": f"Value is above the upper biological reference limit of {upper_limit}.",
                "lower_limit": lower_limit,
                "upper_limit": upper_limit
            }
        else:
            return {
                "status": "Normal",
                "status_reason": "Value is within the biological reference interval.",
                "lower_limit": lower_limit,
                "upper_limit": upper_limit
            }

    # Upper bound only (e.g. < 200, <= 200, ≤ 200, Male <45)
    if upper_limit is not None and lower_limit is None:
        is_strict_less = bool(re.search(r'<\s*\d', ref_str)) and not bool(re.search(r'<=|<=\s*\d', ref_str))
        is_high = (value >= upper_limit) if is_strict_less else (value > upper_limit)
        
        if is_high:
            return {
                "status": "High",
                "status_reason": f"Value is above the upper biological reference limit of {upper_limit}.",
                "lower_limit": None,
                "upper_limit": upper_limit
            }
        else:
            return {
                "status": "Normal",
                "status_reason": "Value is within the biological reference interval.",
                "lower_limit": None,
                "upper_limit": upper_limit
            }

    # Lower bound only (e.g. > 40, >= 40, ≥ 40)
    if lower_limit is not None and upper_limit is None:
        is_strict_greater = bool(re.search(r'>\s*\d', ref_str)) and not bool(re.search(r'>=|>=', ref_str))
        is_low = (value <= lower_limit) if is_strict_greater else (value < lower_limit)

        if is_low:
            return {
                "status": "Low",
                "status_reason": f"Value is below the lower biological reference limit of {lower_limit}.",
                "lower_limit": lower_limit,
                "upper_limit": None
            }
        else:
            return {
                "status": "Normal",
                "status_reason": "Value is within the biological reference interval.",
                "lower_limit": lower_limit,
                "upper_limit": None
            }

    return {
        "status": "Unknown",
        "status_reason": "Reference range missing or cannot be parsed.",
        "lower_limit": None,
        "upper_limit": None
    }
