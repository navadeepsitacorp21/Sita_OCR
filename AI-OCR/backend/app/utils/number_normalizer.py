import re
from typing import Optional


def parse_lakh_format(text: str) -> str:
    """
    Parse textual lakh/lac references (e.g. '1.25 lakh', '2 Lakhs', '3 lakh/cmm', '0.8 lac')
    into standard absolute integer strings before extraction.
    """
    if not text:
        return ""

    def _replace_lakh(match):
        num_part = match.group(1)
        val = float(num_part) * 100000.0
        return str(int(val))

    # Match patterns like 1.25 lakh, 2 Lakhs, 3.5 lac, 1,65 lakh
    pattern = r'\b(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)\b'
    cleaned = re.sub(pattern, _replace_lakh, text, flags=re.IGNORECASE)
    return cleaned


def normalize_number_string(text: str) -> str:
    """
    Step 1: Number Normalization Layer
    Preserves comma-separated values and Indian number formatting (e.g. 1,65,000 -> 165000, 8,000 -> 8000).
    Strips commas from valid numeric patterns while preserving decimal values.
    Supports textual Lakh formats.
    """
    if not text:
        return ""

    # First convert textual lakh/lac numbers if present
    cleaned = parse_lakh_format(text)

    # Replaces commas in numeric patterns like 1,65,000 -> 165000 or 8,000 -> 8000
    def _strip_num_commas(match):
        return match.group(0).replace(",", "")

    # Match multi-group comma-separated integers or floats, e.g. 1,65,000 or 8,000 or 4,50,000.00
    cleaned = re.sub(r'\b\d{1,3}(?:,\d{2,3})+(?:\.\d+)?\b', _strip_num_commas, cleaned)

    return cleaned


def extract_numbers_with_formatting(val_str: str) -> Optional[float]:
    """
    Extract first valid observed numeric value from text string after number normalization.
    """
    if not val_str:
        return None

    normalized_str = normalize_number_string(val_str)

    # Remove stage/grade codes like G3a, G4, G1b, CKD-EPI, etc.
    cleaned = re.sub(r'\b[Gg][1-5][abcABC]?\b', ' ', normalized_str)

    # 1. Decimal search
    decimal_match = re.search(r'(?<![a-zA-Z0-9_])[-+]?\d+\.\d+(?![a-zA-Z0-9_])', cleaned)
    if decimal_match:
        return float(decimal_match.group(0))

    # 2. Integer search
    int_match = re.search(r'(?<![a-zA-Z0-9_])[-+]?\d+(?![a-zA-Z0-9_])', cleaned)
    if int_match:
        return float(int_match.group(0))

    match = re.search(r'(?<![a-zA-Z])[-+]?\d+(?:\.\d+)?', cleaned)
    return float(match.group(0)) if match else None
