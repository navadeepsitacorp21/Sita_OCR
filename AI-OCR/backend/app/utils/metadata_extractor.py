import re
from typing import Dict, Any, Optional


def extract_patient_gender(text: str) -> str:
    """
    Extract patient gender ("male", "female", "unknown") from header text.
    """
    if not text:
        return "unknown"

    # Prioritize line-by-line inspection of header lines containing gender/sex keywords
    for line in text.split("\n"):
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["gender", "sex"]):
            # Avoid reference range lines like "Male <45 Female <35"
            if "<" in line or ">" in line or "ref" in line_lower:
                continue
            if re.search(r'\b(?:m|male)\b', line_lower):
                # Check if female is also present as a standalone word (without female)
                if not re.search(r'\bfemale\b', line_lower) or re.search(r'/\s*male\b|\bsex\s*[:\-]?\s*male', line_lower):
                    return "male"
            if re.search(r'\b(?:f|female)\b', line_lower):
                return "female"

    text_lower = text.lower()
    # General regex matching
    if re.search(r'\b(?:gender|sex)\s*[:\-]?\s*(?:[^\n]*?)\b(?:m|male)\b', text_lower) or re.search(r'\b\d{1,3}\s*y(?:rs)?\s*/\s*m\b', text_lower):
        return "male"

    if re.search(r'\b(?:gender|sex)\s*[:\-]?\s*(?:[^\n]*?)\b(?:f|female)\b', text_lower) or re.search(r'\b\d{1,3}\s*y(?:rs)?\s*/\s*f\b', text_lower):
        return "female"

    return "unknown"


def extract_patient_age(text: str) -> Optional[int]:
    """
    Extract patient age as an integer from text.
    """
    if not text:
        return None

    # Match patterns like "Age: 25 Yrs", "25 Y / M", "Age / Sex : 28 / Female"
    match = re.search(r'\b(?:age|age\s*/\s*sex|age\s*/\s*gender)\s*[:\-]?\s*(\d{1,3})\b', text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    match_years = re.search(r'\b(\d{1,3})\s*(?:years|yrs|y/o|y)\b', text, re.IGNORECASE)
    if match_years:
        return int(match_years.group(1))

    return None


def extract_patient_name(text: str) -> Optional[str]:
    """
    Extract patient name from header text.
    """
    if not text:
        return None

    match = re.search(r'\b(?:patient name|name|pt\.?\s*name)\s*[:\-]?\s*([A-Za-z\.\s]+?)(?:\s+(?:age|sex|gender|uhid|mrn|date|ref|id)\b|\n|$)', text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        if len(name) > 2 and not any(kw in name.lower() for kw in ["report", "test", "laboratory", "diagnostics"]):
            return name
    return None


def extract_patient_id(text: str) -> Optional[str]:
    """
    Extract UHID / MRN / Patient ID from header text.
    """
    if not text:
        return None

    match = re.search(r'\b(?:uhid\s*(?:/\s*reg\s*no)?|mrn|patient\s*id|patient\s*no|reg\.?\s*no|pid)\s*[:\-]?\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)
    if match:
        val = match.group(1).strip().strip("/")
        if val and len(val) > 2:
            return val
    return None


def extract_report_id(text: str) -> Optional[str]:
    """
    Extract Report ID / Lab No / Accession No from text.
    """
    if not text:
        return None

    match = re.search(r'\b(?:report id|lab no|acc no|accession no|bill no|invoice no)\s*[:\-]?\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_report_date(text: str) -> Optional[str]:
    """
    Extract report or collection date string.
    """
    if not text:
        return None

    match = re.search(r'\b(?:date|collected|reported)\s*[:\-]?\s*(\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3})[\/\-\.]\d{2,4})', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    date_match = re.search(r'\b(\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3})[\/\-\.]\d{2,4})\b', text)
    if date_match:
        return date_match.group(1).strip()

    return None


def extract_hospital_name(text: str) -> Optional[str]:
    """
    Extract hospital or laboratory brand name.
    """
    if not text:
        return None

    for line in text.split("\n")[:8]:
        line_clean = line.strip()
        if any(kw in line_clean.lower() for kw in ["hospital", "diagnostics", "pathlabs", "clinic", "lab", "health"]):
            if any(kw in line_clean.lower() for kw in ["patient", "report date", "result"]):
                continue
            # Strip report title suffixes like " - LIVER FUNCTION TEST REPORT"
            cleaned_brand = re.sub(r'\s*[\-\|].*$', '', line_clean)
            if len(cleaned_brand) > 3:
                return cleaned_brand
            return line_clean
    return None


def extract_metadata(ocr_text: str) -> Dict[str, Any]:
    """
    Step 2: Reusable metadata extractor for lab reports.
    Returns patient, report, and hospital structured dictionaries.
    """
    header_text = "\n".join(ocr_text.split("\n")[:20]) if ocr_text else ""

    gender = extract_patient_gender(header_text)
    age = extract_patient_age(header_text)
    name = extract_patient_name(header_text)
    pid = extract_patient_id(header_text)

    rid = extract_report_id(header_text)
    rdate = extract_report_date(header_text)

    hname = extract_hospital_name(header_text)

    return {
        "patient": {
            "name": name,
            "age": age,
            "gender": gender,
            "patient_id": pid
        },
        "report": {
            "report_id": rid,
            "report_date": rdate
        },
        "hospital": {
            "name": hname
        }
    }
