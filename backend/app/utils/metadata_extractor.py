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
    # Handle OCR typo for male (e.g. 'eale / 1990' or 'male / 1990')
    if re.search(r'\b(?:male|eale)\s*/\s*\d{4}', text_lower):
        return "male"
    if re.search(r'\bfemale\s*/\s*\d{4}', text_lower):
        return "female"

    # General regex matching
    if re.search(r'\b(?:gender|sex)\s*[:\-]?\s*(?:[^\n]*?)\b(?:m|male)\b', text_lower) or re.search(r'\b\d{1,3}\s*y(?:rs|ears)?\s*/\s*(?:m|male)\b', text_lower):
        return "male"

    if re.search(r'\b(?:gender|sex)\s*[:\-]?\s*(?:[^\n]*?)\b(?:f|female)\b', text_lower) or re.search(r'\b\d{1,3}\s*y(?:rs|ears)?\s*/\s*(?:f|female)\b', text_lower):
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

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line_idx, line in enumerate(lines[:12]):
        if re.search(r'\bage\s*[:\-]?\s*\d+', line, re.IGNORECASE):
            prev_lines = lines[:line_idx]
            if prev_lines:
                cand = prev_lines[-1]
                if re.match(r'^[A-Z][a-zA-Z\.\s]{2,40}$', cand):
                    if not any(kw in cand.lower() for kw in ["sample", "hospital", "lab", "complex", "road", "dr.", "doctor", "pathology", "diagnostics", "patient details", "accurate", "caring", "instant"]):
                        return cand
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


import datetime

MONTHS_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def normalize_date_string(date_str: str, doc_context: Optional[str] = None) -> Optional[str]:
    """
    Normalizes dates from reliable lab formats into standard DD/MM/YYYY.
    Supported unambiguous formats:
      - ISO: YYYY-MM-DD (e.g. 2021-11-07, 2025-10-08)
      - Explicit named months: DD-Mon-YYYY or Mon DD, YYYY (e.g. 07-Nov-2021, Nov 07, 2021)
      - Unambiguous numeric dates where first number > 12 (must be day) e.g. 25/08/2021
      - Numeric dates with month > 12 e.g. 07/11/2021 when document context establishes DD/MM/YYYY
        (e.g. Aster Clinics, Indian / UAE lab standards, or explicit dd/mm/yyyy format headers).
      - Truly ambiguous dates (e.g. 03/04/2021) without reliable document context return None.
      - Invalid calendar dates (e.g. 31/02/2021) return None.
    """
    if not date_str:
        return None

    cleaned = re.sub(r'[\)\(\]\[]', '/', str(date_str)).strip()

    # Clean OCR artifacts on year if preceded by a recognized month name:
    # e.g., '02 Dec, 2X' -> '02 Dec, 22', '02 Dec 202X' -> '02 Dec 2022'
    cleaned = re.sub(r'([A-Za-z]{3,9}[,\s\/\-\.]*)202[Xx]\b', r'\g<1>2022', cleaned)
    cleaned = re.sub(r'([A-Za-z]{3,9}[,\s\/\-\.]*)2[Xx]\b', r'\g<1>22', cleaned)

    # Pattern 1: ISO format YYYY-MM-DD (e.g. 2021-11-07)
    m_iso = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})', cleaned)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        try:
            valid_date = datetime.date(y, m, d)
            return valid_date.strftime("%d/%m/%Y")
        except ValueError:
            return None

    # Pattern 2: Month name first: "Nov 07, 2021" or "Nov 7 2021"
    m_mon_first = re.match(r'^([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s*|\s+)(\d{2,4})', cleaned)
    if m_mon_first:
        mon_str = m_mon_first.group(1).lower()[:3]
        d = int(m_mon_first.group(2))
        y = int(m_mon_first.group(3))
        if y < 100:
            y += 2000
        m = MONTHS_MAP.get(mon_str)
        if m:
            try:
                valid_date = datetime.date(y, m, d)
                return valid_date.strftime("%d/%m/%Y")
            except ValueError:
                return None

    # Pattern 3: Day first with month name: "07-Nov-2021", "08-Oct-2025", "7 Nov 2021", "02Dec,22", "02 Dec, 22", "01Jun2026"
    m_day_mon = re.match(r'^(\d{1,2})[\/\-\.\s]?([A-Za-z]{3,9})[,\/\-\.\s]*(\d{2,4})', cleaned)
    if m_day_mon:
        d = int(m_day_mon.group(1))
        mon_str = m_day_mon.group(2).lower()[:3]
        y = int(m_day_mon.group(3))
        if y < 100:
            y += 2000
        m = MONTHS_MAP.get(mon_str)
        if m:
            try:
                valid_date = datetime.date(y, m, d)
                return valid_date.strftime("%d/%m/%Y")
            except ValueError:
                return None

    # Pattern 4: Numeric date e.g. "07/11/2021", "25/08/2021", "03/04/2021"
    m_num = re.match(r'^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', cleaned)
    if m_num:
        p1 = int(m_num.group(1))
        p2 = int(m_num.group(2))
        y = int(m_num.group(3))
        if y < 100:
            y += 2000

        # Check calendar validity for both interpretations:
        # A: DD/MM/YYYY -> p1 is day, p2 is month
        valid_a = None
        try:
            valid_a = datetime.date(y, p2, p1)
        except ValueError:
            pass

        # B: MM/DD/YYYY -> p2 is day, p1 is month
        valid_b = None
        try:
            valid_b = datetime.date(y, p1, p2)
        except ValueError:
            pass

        # Case 1: Both invalid (e.g. 31/02/2021)
        if valid_a is None and valid_b is None:
            return None

        # Case 2: Only one is valid:
        # e.g. 25/08/2021 -> valid_a is valid (p1=25 day, p2=8 month), valid_b invalid (p1=25 not month)
        if valid_a is not None and valid_b is None:
            return valid_a.strftime("%d/%m/%Y")
        if valid_b is not None and valid_a is None:
            return valid_b.strftime("%d/%m/%Y")

        # Case 3: Both are valid (e.g. 03/04/2021 or 07/11/2021 where p1<=12 and p2<=12)
        # If p1 == p2 (e.g. 05/05/2021), it is identical in both formats
        if p1 == p2 and valid_a is not None:
            return valid_a.strftime("%d/%m/%Y")

        # Document context check:
        # If document contains explicit format hints (e.g. 'dd/mm/yyyy', 'dd-mm-yyyy')
        # or known DD/MM/YYYY lab providers (e.g. Aster, Apollo, Care, Dr Lal, SRL, Thyrocare, Metropolis)
        if doc_context:
            ctx_lower = doc_context.lower()
            if any(h in ctx_lower for h in ["dd/mm", "dd-mm", "dd.mm", "aster", "care diagnostics", "dr lal", "srl", "metropolis", "apollo"]):
                return valid_a.strftime("%d/%m/%Y")
            if any(h in ctx_lower for h in ["mm/dd", "mm-dd"]):
                return valid_b.strftime("%d/%m/%Y")

        # Truly ambiguous without reliable document context: DO NOT GUESS
        return None

    return None


def extract_laboratory_dates(text: str) -> Dict[str, Optional[str]]:
    """
    Extract distinct laboratory lifecycle dates preserving their clinical semantic meaning:
      - collection_date (Collected On / Sample Collected / Specimen Collected)
      - reported_date (Reported On / Result Date / Verified Date)
      - received_date (Received On)
      - ordered_date (Ordered On / Registered On)
      - primary_report_date (prioritized: collection_date > reported_date > generic report date)
    """
    dates: Dict[str, Optional[str]] = {
        "report_date": None,
        "collection_date": None,
        "reported_date": None,
        "received_date": None,
        "ordered_date": None,
    }
    if not text:
        return dates

    # Date regex with OCR noise tolerance (e.g., 07)11/2021 or 07/11/2021 or 08-Oct-2025 or 2025-10-08 or 02Dec,22 or 01Jun2026 or 02 Dec 2X)
    date_regex = r'(\d{1,2}\s*[A-Za-z]{3,9}[,\s\/\-\.]*(?:\d{1,3}[Xx]|\d{2,4})|\d{1,2}[\/\-\.\)][A-Za-z0-9]{1,3}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})'

    lines = text.split("\n")
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        line_lower = line_clean.lower()

        # Check subsequent lines (up to 4 lines ahead) because OCR can interleave columns:
        forward_text = " ".join([l.strip() for l in lines[idx:min(idx + 5, len(lines))]])

        # 1. Collection date (e.g. Cellected On, Collected On, Sample Collected)
        if any(kw in line_lower for kw in ["collect", "cellect", "sample date", "specimen date"]):
            if not dates["collection_date"]:
                for m in re.finditer(date_regex, forward_text):
                    norm = normalize_date_string(m.group(1), doc_context=text)
                    if norm:
                        dates["collection_date"] = norm
                        break

        # 2. Reported date (e.g. Reported On, grgarted 0n, Result Date, Approved Date)
        if any(kw in line_lower for kw in ["report", "grgarted", "result date", "auth", "verified"]):
            # Avoid report id / report type lines unless it contains date keywords
            if any(w in line_lower for w in ["reported", "report date", "grgarted", "result date"]):
                if not dates["reported_date"]:
                    for m in re.finditer(date_regex, forward_text):
                        norm = normalize_date_string(m.group(1), doc_context=text)
                        if norm:
                            dates["reported_date"] = norm
                            break

        # 3. Received date
        if any(kw in line_lower for kw in ["received", "recevied"]):
            if not dates["received_date"]:
                for m in re.finditer(date_regex, forward_text):
                    norm = normalize_date_string(m.group(1), doc_context=text)
                    if norm:
                        dates["received_date"] = norm
                        break

        # 4. Ordered / Registered date
        if any(kw in line_lower for kw in ["ordered", "oedered", "registered", "booking date"]):
            if not dates["ordered_date"]:
                for m in re.finditer(date_regex, forward_text):
                    norm = normalize_date_string(m.group(1), doc_context=text)
                    if norm:
                        dates["ordered_date"] = norm
                        break

        # 5. Generated date (secondary fallback for reported date)
        if any(kw in line_lower for kw in ["generated", "printed"]):
            if not dates["reported_date"]:
                for m in re.finditer(date_regex, forward_text):
                    norm = normalize_date_string(m.group(1), doc_context=text)
                    if norm:
                        dates["reported_date"] = norm
                        break

    # Fallback search for general report date label
    if not any([dates["collection_date"], dates["reported_date"]]):
        for m in re.finditer(r'\b(?:date|collected|reported|generated)\s*[:\-]?\s*' + date_regex, text, re.IGNORECASE):
            raw_val = m.group(1).strip()
            norm = normalize_date_string(raw_val, doc_context=text)
            if norm:
                dates["reported_date"] = norm
                break

    # Priority for primary medical report date:
    # 1. collection_date (when specimen was taken)
    # 2. reported_date (when laboratory certified the results)
    # 3. received_date / ordered_date
    raw_primary = (
        dates["collection_date"]
        or dates["reported_date"]
        or dates["received_date"]
        or dates["ordered_date"]
    )
    dates["report_date"] = raw_primary

    return dates


def extract_report_date(text: str) -> Optional[str]:
    """
    Extract report or collection date string.
    Only returns validated, unambiguous dates. Rejects ambiguous (e.g. 03/04/2021)
    or invalid numeric ranges.
    """
    if not text:
        return None

    # First check explicit date label on the same line
    match = re.search(r'\b(?:report\s*date|collected\s*on|reported\s*on|collection\s*date|date)\s*[:\-]?\s*([A-Za-z0-9\/\-\.\,]+(?:[^\S\r\n]+[A-Za-z0-9\/\-\.\,]+)?)', text, re.IGNORECASE)
    if match:
        raw_val = match.group(1).strip()
        # Clean fused time suffix like 22Sep202512:45PM -> 22Sep2025
        fused_match = re.match(r'^(\d{1,2}(?:[\-\/\s]?[A-Za-z]{3}[\-\/\s]?|\s+[A-Za-z]{3}\s+)\d{4})', raw_val)
        if fused_match:
            raw_val = fused_match.group(1).strip()
        norm = normalize_date_string(raw_val, doc_context=text)
        if norm:
            # Check if original was named month like 08-Oct-2025 or 22 Sep 2025
            if re.search(r'[A-Za-z]{3}', raw_val):
                return raw_val
            return norm

    # Fall back to structured laboratory date extractor
    dates = extract_laboratory_dates(text)
    return dates.get("report_date")


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


def clean_interpretation_text(text: str) -> str:
    """
    Cleans OCR artifacts and concatenations in laboratory interpretation text.
    e.g. 'Furtherconfirmfor Anemia' -> 'Further confirm for Anemia'
    """
    cleaned = text.strip()
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    cleaned = re.sub(r'\b(further)(confirm)(for)\b', r'\1 \2 \3', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(confirm)(for)\b', r'\1 \2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(further)(confirm)\b', r'\1 \2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def extract_report_interpretation(text: str) -> Optional[Dict[str, str]]:
    """
    Extract free-text clinical notes, impressions, or interpretations printed by the laboratory.
    Preserves the laboratory's comment as verbatim source metadata without converting it into a diagnosis.
    Returns: {"text": str, "source": "report"} or None
    """
    if not text:
        return None

    lines = [l.strip() for l in text.split("\n")]
    for idx, line_clean in enumerate(lines):
        # 1. Single line: "Interpretation: Further confirm for Anemia"
        m = re.match(
            r'^(?:interpretation|impression|clinical\s*notes?|lab\s*notes?|comment|comments|comments\s*/\s*interpretation)\s*[:\-]\s*(.*)$',
            line_clean,
            re.IGNORECASE
        )
        if m:
            raw_content = m.group(1).strip()
            # If content is on subsequent lines (e.g. Header on its own line)
            if not raw_content and idx + 1 < len(lines):
                next_parts = []
                for nxt in lines[idx + 1:idx + 6]:
                    if not nxt or any(stop in nxt.lower() for stop in ["*** end", "end of report", "dr.", "pathologist", "note:"]):
                        break
                    next_parts.append(nxt)
                raw_content = " ".join(next_parts).strip()

            if len(raw_content) > 3 and not re.search(r'^(?:see below|attached|nil|na|n/a)$', raw_content, re.IGNORECASE):
                cleaned_text = clean_interpretation_text(raw_content)
                return {
                    "text": cleaned_text,
                    "source": "report"
                }
    return None


def extract_metadata(ocr_text: str) -> Dict[str, Any]:
    """
    Step 2: Reusable metadata extractor for lab reports.
    Returns patient, report, and hospital structured dictionaries.
    Preserves distinct semantic dates (collection, reported, received, ordered)
    and laboratory source interpretations.
    """
    header_text = "\n".join(ocr_text.split("\n")[:30]) if ocr_text else ""

    gender = extract_patient_gender(header_text)
    if gender == "unknown" and ocr_text:
        gender = extract_patient_gender(ocr_text)

    age = extract_patient_age(header_text)
    if age is None and ocr_text:
        age = extract_patient_age(ocr_text)

    name = extract_patient_name(header_text)
    pid = extract_patient_id(header_text)

    rid = extract_report_id(header_text)
    rdate = extract_report_date(header_text)
    lab_dates = extract_laboratory_dates(header_text)

    # If dates were not found in header, scan full text
    if not lab_dates.get("report_date") and ocr_text:
        full_dates = extract_laboratory_dates(ocr_text)
        for k_d, v_d in full_dates.items():
            if v_d and not lab_dates.get(k_d):
                lab_dates[k_d] = v_d
        if not rdate:
            rdate = extract_report_date(ocr_text)

    effective_report_date = rdate or lab_dates.get("report_date")
    if effective_report_date:
        lab_dates["report_date"] = effective_report_date

    hname = extract_hospital_name(header_text)
    interpretation = extract_report_interpretation(ocr_text)

    return {
        "patient": {
            "name": name,
            "age": age,
            "gender": gender,
            "patient_id": pid
        },
        "report": {
            "report_id": rid,
            "report_date": lab_dates.get("report_date"),
            "collection_date": lab_dates.get("collection_date"),
            "reported_date": lab_dates.get("reported_date"),
            "received_date": lab_dates.get("received_date"),
            "ordered_date": lab_dates.get("ordered_date"),
            "report_interpretation": interpretation,
        },
        "hospital": {
            "name": hname
        },
        "report_interpretation": interpretation,
    }
