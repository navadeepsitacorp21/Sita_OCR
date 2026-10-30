import re
from typing import Tuple, Optional
from app.utils.number_normalizer import normalize_number_string, extract_numbers_with_formatting


def normalize_ocr_text(text: str) -> str:
    """
    Step 1: OCR Normalization Layer
    Fixes common OCR character substitutions in numeric positions:
    - n0.XX / N0.XX / O0.XX / o0.XX -> 80.XX
    - l0.XX / I0.XX / |0.XX -> 10.XX
    - S0.XX / s0.XX -> 50.XX
    - Normalizes multiplication symbols and units (×10³/µL -> 10^3/uL, gm/dL -> g/dL)
    - Removes duplicated whitespace
    """
    if not text:
        return ""

    cleaned = text
    # 1. OCR character substitution for leading digits before decimal point
    cleaned = re.sub(r'(?<![a-zA-Z0-9])[nNoOBb]0\.(\d+)', r'80.\1', cleaned)
    cleaned = re.sub(r'(?<![a-zA-Z0-9])[lI|]0\.(\d+)', r'10.\1', cleaned)
    cleaned = re.sub(r'(?<![a-zA-Z0-9])[sS]0\.(\d+)', r'50.\1', cleaned)

    # 2. Normalize decimal spacing e.g. 80 . 30 -> 80.30
    cleaned = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', cleaned)

    # 3. Normalize multiplication signs and unit unicode characters
    cleaned = re.sub(r'[×xX]\s*10\s*[\^3*3³]\s*/\s*[μuU][lL]', '10^3/uL', cleaned)
    cleaned = re.sub(r'10\s*[\^3*3³]\s*/\s*[μuU][lL]', '10^3/uL', cleaned)
    cleaned = re.sub(r'[×xX]\s*10\s*[\^6*6⁶]\s*/\s*[μuU][lL]', '10^6/uL', cleaned)
    cleaned = re.sub(r'10\s*[\^6*6⁶]\s*/\s*[μuU][lL]', '10^6/uL', cleaned)
    cleaned = re.sub(r'\bgm\s*/\s*dL\b', 'g/dL', cleaned, flags=re.IGNORECASE)

    # 4. Standardize en-dash/em-dash in range to hyphen
    cleaned = re.sub(r'[–—]', '-', cleaned)

    # 5. Fix OCR typos in gender labels and comparison symbols in ranges (e.g. "Mele: ?55" -> "Male: <55", "Mele: \xd755" -> "Male: <55", "?40" -> "<40")
    cleaned = re.sub(r'\bmele\b', 'Male', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(male|female|m|f)\s*:\s*[?×\u00d7]\s*(\d+)', r'\1: <\2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(male|female|m|f)\s*:\s*\?(\d+)', r'\1: <\2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(male|female|m|f)\s*:\s*(\d+)', r'\1: <\2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+[?×\u00d7]\s*(\d+)', r' <\1', cleaned)
    cleaned = re.sub(r'\s+\?(\d+)', r' <\1', cleaned)

    return cleaned


def clean_text(text: str) -> str:
    """
    Clean raw OCR output by standardizing line breaks, fixing OCR substitutions, and removing redundant spacing.
    """
    if not text:
        return ""
    text = re.sub(r'\r\n|\r', '\n', text)
    text = normalize_ocr_text(text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_numbers(val_str: str) -> Optional[float]:
    """
    Extract first valid observed numeric value from text string after number normalization.
    """
    return extract_numbers_with_formatting(val_str)


# Known medical unit regex patterns (ordered with longer/composite units first)
KNOWN_UNITS = [
    r'10\^3\s*/\s*[μuU]L',
    r'10\^6\s*/\s*[μuU]L',
    r'x\s*10\^3\s*/\s*[μuU]L',
    r'x\s*10\^6\s*/\s*[μuU]L',
    r'10\*3\s*/\s*[μuU]L',
    r'10\*6\s*/\s*[μuU]L',
    r'mL\s*/\s*min\s*/\s*1\.73m[²2]',
    r'mL\s*/\s*min',
    r'cells\s*/\s*cu\.?mm',
    r'cells\s*/\s*cumm',
    r'cells\s*/\s*cmm',
    r'/\s*cu\.?mm',
    r'/\s*cumm',
    r'/\s*cmm',
    r'/\s*mm3',
    r'/\s*[μuU]L',
    r'µIU\s*/\s*mL',
    r'uIU\s*/\s*mL',
    r'µg\s*/\s*dL',
    r'ug\s*/\s*dL',
    r'µg\s*/\s*mL',
    r'ug\s*/\s*mL',
    r'pg\s*/\s*mL',
    r'ng\s*/\s*mL',
    r'ng\s*/\s*dL',
    r'gm\s*/\s*dL',
    r'g\s*/\s*dL',
    r'gm\s*/\s*dl',
    r'g\s*/\s*dl',
    r'gm\s*%',
    r'g\s*%',
    r'mg\s*/\s*dL',
    r'mg\s*/\s*dl',
    r'mmol\s*/\s*L',
    r'µmol\s*/\s*L',
    r'umol\s*/\s*L',
    r'IU\s*/\s*mL',
    r'IU\s*/\s*L',
    r'U\s*/\s*L',
    r'u\s*/\s*l',
    r'ratio',
    r'fL',
    r'fl',
    r'pg',
    r'%'
]

UNIT_REGEX = re.compile(r'|'.join(KNOWN_UNITS), re.IGNORECASE)

# Number pattern supporting commas e.g. "4,000", "1,60,000", "12.5"
_NUM_P = r'(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?'

# Gender-specific reference range regex (e.g. "Male <45 Female <35", "Male: 10-50 Female: 10-35", "M: <40, F: <35", "Male 40 Female <35")
GENDER_RANGE_REGEX = re.compile(
    r'(?:(?:male|m)\b\s*[:\-]?\s*(?:[<≤>≥]=?\s*' + _NUM_P + r'|' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'|\d+(?:\.\d+)?)\s*(?:/|,|;)?\s*)'
    r'(?:(?:female|f)\b\s*[:\-]?\s*(?:[<≤>≥]=?\s*' + _NUM_P + r'|' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'|\d+(?:\.\d+)?))|'
    r'(?:(?:female|f)\b\s*[:\-]?\s*(?:[<≤>≥]=?\s*' + _NUM_P + r'|' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'|\d+(?:\.\d+)?)\s*(?:/|,|;)?\s*)'
    r'(?:(?:male|m)\b\s*[:\-]?\s*(?:[<≤>≥]=?\s*' + _NUM_P + r'|' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'|\d+(?:\.\d+)?))',
    re.IGNORECASE
)

# Reference range pattern supporting commas e.g. "4,000 - 11,000", "1,60,000 - 4,50,000", "12.5-16.0", "< 200", "(36-46)"
RANGE_REGEX = re.compile(
    r'(?:\(\s*[<≤>≥]=?\s*' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'\s*%?\s*\))|'
    r'(?:\(\s*[<≤>≥]=?\s*' + _NUM_P + r'\s*%?\s*\))|'
    r'(?:\(\s*' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'\s*%?\s*\))|'
    r'(?:[<≤>≥]=?\s*' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'\s*%?)|'
    r'(?:[<≤>≥]=?\s*' + _NUM_P + r'\s*%?)|'
    r'(?:\b' + _NUM_P + r'\s*(?:-|to|–|—)\s*' + _NUM_P + r'\s*%?\b)',
    re.IGNORECASE
)


def extract_unit(text: str) -> Optional[str]:
    """
    Find known unit string in text.
    """
    match = UNIT_REGEX.search(text)
    return match.group(0).strip() if match else None


def extract_reference_range(text: str) -> Tuple[Optional[str], str]:
    """
    Extract biological reference range string from line (e.g. '12.5-16', '4,000 - 11,000', '<200', '(36-46)', 'Male <45 Female <35').
    Returns (cleaned_range, source) where source is 'report' or 'none'.
    """
    if not text:
        return None, "none"

    # 1. Check for gender-specific range patterns first (e.g. "Male <45 Female <35")
    gender_match = GENDER_RANGE_REGEX.search(text)
    if gender_match:
        res = gender_match.group(0).strip()
        if res.startswith('(') and res.endswith(')'):
            res = res[1:-1].strip()
        return res, "report"

    # 2. Check for standard bounded/single-bound reference ranges
    match = RANGE_REGEX.search(text)
    if match:
        res = match.group(0).strip()
        # Clean wrapping parentheses if present
        if res.startswith('(') and res.endswith(')'):
            res = res[1:-1].strip()
        # Strip trailing % if included in reference match for clean numeric comparison
        res = res.rstrip('%').strip()
        return res, "report"
    return None, "none"


def parse_line_components(line: str, default_unit: str = "") -> Tuple[Optional[float], str, str, str]:
    """
    Extract observed numeric value, unit, reference range, and reference source from line segment.
    Ensures RESULT VALUE > REFERENCE VALUE by stripping reference range contexts
    (including gender prefixes and interval numbers) before numeric extraction.
    Returns (value, unit, reference_range, reference_source).
    """
    ref_range_raw, ref_source = extract_reference_range(line)
    ref_range = ref_range_raw or ""

    # Remove reference range from text to avoid picking numbers from ref range
    line_without_ref = line
    if ref_range_raw:
        line_without_ref = line_without_ref.replace(f"({ref_range_raw})", " ")
        line_without_ref = line_without_ref.replace(ref_range_raw, " ")

    # Strip any remaining gender reference labels or comparison fragments
    line_without_ref = re.sub(r'\b(?:male|female|m|f)\b\s*[:\-]?\s*(?:[<≤>≥]=?\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:-|to|–|—)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)?', ' ', line_without_ref, flags=re.IGNORECASE)
    line_without_ref = re.sub(r'[<≤>≥]=?\s*\d+(?:\.\d+)?', ' ', line_without_ref)

    unit = extract_unit(line) or default_unit

    # Remove unit text before extracting numeric value to avoid conflicts
    if unit and unit != default_unit:
        line_without_ref = line_without_ref.replace(unit, " ")

    value = extract_numbers(line_without_ref)

    return value, unit, ref_range, ref_source
