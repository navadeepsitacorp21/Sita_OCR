import re
from typing import Optional, Tuple, List, Dict, Any
from app.utils.text_utils import parse_line_components

# Patterns that indicate document headers, administrative metadata, or non-result text
METADATA_PATTERNS = [
    r'\b(?:patient\s*id|patientid|patient\s*no|uhid|lab\s*id|report\s*id)\b',
    r'\b(?:accession|sample\s*id|specimen\s*id|barcode|qr\s*code)\b',
    r'\b(?:registration\s*no|reg\s*no|mrn|ipd|opd|bill\s*no|invoice\s*no)\b',
    r'\b(?:phone|mobile|tel|contact|email|address|hospital|laboratory|clinic)\b',
    r'\b(?:dob|age\s*/\s*sex|gender|referred\s*by|ref\s*by|doctor|dr\.)\b',
    r'\b(?:home\s*collection|collected\s*at|center\s*name)\b',
    r'\b(?:date\s*&?\s*time|time\s*of\s*collection|date\s*of\s*collection)\b',
    r'\b(?:received\s*on|released\s*on|reported\s*on|registered\s*on)\b',
    r'\b(?:collected\s*on|sample\s*collected|specimen\s*received)\b',
    r'\b(?:method\s*:|methodology|technology|principle\s*:)\b',
    r'\b(?:page\s*\d+\s*of\s*\d+|page\s*no|page\s*:)\b',
    r'\b(?:signature|electronically\s*verified|authorized\s*signatory)\b',
    r'(?:end\s*of\s*report|\*{3}\s*end\s*of\s*report|final\s*report)'
]

METADATA_REGEX = re.compile('|'.join(METADATA_PATTERNS), re.IGNORECASE)

# Patterns that indicate section headers / test panel titles (not individual test rows)
TITLE_PATTERNS = [
    r'^\s*(?:test\s*name\s*:\s*)?(?:vitamin(?:\s+[a-z0-9]+)?|thyroid|lipid|liver|kidney|renal|cbc|complete\s*blood\s*count|diabetes)\s*(?:profile|panel|report|tests?)\s*$',
    r'^\s*test\s*name\s*:\s*[a-zA-Z\s0-9\(\)\-_]+\s*(?:profile|panel)\s*$',
    r'\binvestigation\b.*\b(?:observed|value|result|unit|reference|interval)\b',
    r'\btest\s*name\b.*\b(?:result|observed|value|unit|reference|ref\s*range)\b'
]

TITLE_REGEX = re.compile('|'.join(TITLE_PATTERNS), re.IGNORECASE)

# Biomarkers with physiological upper bounds to reject misparsed IDs / dates / phones
BIOMARKER_MIN_LIMITS: Dict[str, float] = {
    "mcv": 50.0,
    "mchc": 25.0,
    "mch": 10.0,
    "hemoglobin": 3.0,
    "pcv": 15.0,
    "rdw": 5.0,
}

BIOMARKER_MAX_LIMITS: Dict[str, float] = {
    "mcv": 130.0,
    "mchc": 40.0,
    "mch": 50.0,
    "hemoglobin": 25.0,
    "rbc_count": 10.0,
    "pcv": 75.0,
    "rdw": 35.0,
    "vitamin_d": 300.0,
    "vitamin_b12": 3000.0,
    "vitamin_b1": 50.0,
    "vitamin_b2": 100.0,
    "vitamin_b3": 50.0,
    "vitamin_b5": 500.0,
    "vitamin_b6": 200.0,
    "vitamin_b7": 50.0,
    "folate": 100.0,
    "ferritin": 5000.0,
    "iron": 1000.0,
    "hba1c": 25.0,
    "tsh": 150.0,
    "total_t3": 20.0,
    "total_t4": 50.0,
    "free_t3": 20.0,
    "free_t4": 20.0,
    "serum_creatinine": 30.0,
    "blood_urea": 400.0,
    "blood_urea_nitrogen": 200.0,
    "uric_acid": 30.0,
    "calcium": 25.0,
    "phosphorus": 25.0,
    "magnesium": 15.0,
    "total_bilirubin": 50.0,
    "direct_bilirubin": 30.0,
    "indirect_bilirubin": 30.0,
    "total_cholesterol": 1000.0,
    "triglycerides": 3000.0,
    "hdl_cholesterol": 200.0,
    "ldl_cholesterol": 500.0,
}


def is_metadata_line(line: str) -> bool:
    """
    Check if an OCR line contains administrative metadata such as patient ID, barcode,
    collection timestamp, method, or doctor details.
    """
    if not line:
        return False
    return bool(METADATA_REGEX.search(line))


def is_report_title_line(line: str) -> bool:
    """
    Check if an OCR line is a section header or report title rather than a test result row.
    """
    if not line:
        return False
    return bool(TITLE_REGEX.search(line))


def clean_line_from_metadata(line: str) -> str:
    """
    Strip embedded metadata patterns, dates, timestamps, phone numbers, and alphanumeric IDs
    from a test result row before numeric extraction.
    """
    if not line:
        return ""
    
    cleaned = line

    # 1. Remove dates (e.g. 24/06/2023, 24-06-2023, 2023-06-24, 24.06.2023)
    cleaned = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ' ', cleaned)
    cleaned = re.sub(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', ' ', cleaned)

    # 2. Remove timestamps (e.g. 09:12:00, 09:12, 14:30 PM, 14:30:15)
    cleaned = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?\b', ' ', cleaned)

    # 3. Remove phone / 10+ digit continuous numbers
    cleaned = re.sub(r'\b\d{10,}\b', ' ', cleaned)

    # 4. Remove alphanumeric IDs / barcodes / codes (e.g. PK22638485, MH20230088, ID99834)
    cleaned = re.sub(r'\b[A-Za-z]+[0-9]{3,}[A-Za-z0-9]*\b', ' ', cleaned)
    cleaned = re.sub(r'\b[0-9]{3,}[A-Za-z]+[A-Za-z0-9]*\b', ' ', cleaned)

    # 5. Remove long integers (>6 digits) that are clearly IDs
    cleaned = re.sub(r'\b\d{7,9}\b', ' ', cleaned)

    return re.sub(r'\s+', ' ', cleaned).strip()


def validate_biomarker_value(key: str, value: Optional[float], unit: str = "") -> Tuple[bool, str]:
    """
    Validate an extracted numeric value against biological limits for the given biomarker.
    Returns (is_valid, reason).
    """
    if value is None:
        return False, "Value is None"

    if value < 0:
        # Most biomarkers cannot be negative
        if key not in ["base_excess"]:
            return False, f"Negative value {value} invalid for {key}"

    min_limit = BIOMARKER_MIN_LIMITS.get(key)
    if min_limit is not None and value < min_limit:
        return False, f"Physiological range mismatch: Value {value} is below lower biological threshold of {min_limit} for {key}"

    max_limit = BIOMARKER_MAX_LIMITS.get(key)
    if max_limit is not None and value > max_limit and value < 1000:
        return False, f"Physiological range mismatch: Value {value} exceeds biological threshold of {max_limit} for {key}"

    return True, "passed"
