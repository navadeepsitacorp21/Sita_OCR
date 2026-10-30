import re
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

from app.utils.text_utils import extract_reference_range, GENDER_RANGE_REGEX


@dataclass
class ReferenceResolution:
    reference_range: str = ''
    reference_source: str = 'unknown'
    reference_type: str = 'unknown'
    low: Optional[float] = None
    high: Optional[float] = None
    is_gender_specific: bool = False
    raw_report_candidate: str = ''


def clean_reference_string(ref: str) -> str:
    if not ref:
        return ''
    ref = re.sub(r'(?i)\b(?:calculated|calrulated|impedance|automated|flow|cytometric|cytemetric)\b.*', '', ref)
    ref = re.sub(r'\b\d{1,3}(?:,\d{2,3})+(?:\.\d+)?\b', lambda m: m.group(0).replace(',', ''), ref)
    ref = re.sub(r'(\d{1,2}\.\d)(1\d\.\d)', r'\1 - \2', ref)
    cleaned = re.sub(r'(\d+(?:\.\d+)?)\s*[^\d\s\.]+\s*(\d+(?:\.\d+)?)', r'\1 - \2', ref)
    cleaned = re.sub(r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', r'\1 - \2', cleaned)
    cleaned = re.sub(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', r'\1 - \2', cleaned)
    return cleaned.strip()


_UPPER_BOUND_RE = re.compile(r'^[<\u2264]=?\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
_LOWER_BOUND_RE = re.compile(r'^[>\u2265]=?\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
_RANGE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|to|\u2013|\u2014)\s*(\d+(?:\.\d+)?)', re.IGNORECASE)


def detect_reference_type(ref: str) -> Tuple[str, Optional[float], Optional[float]]:
    if not ref:
        return 'unknown', None, None
    if GENDER_RANGE_REGEX.search(ref):
        return 'gender_specific', None, None
    m = _UPPER_BOUND_RE.match(ref.strip())
    if m:
        return 'upper_bound', None, float(m.group(1))
    m = _LOWER_BOUND_RE.match(ref.strip())
    if m:
        return 'lower_bound', float(m.group(1)), None
    m = _RANGE_RE.search(ref)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return 'range', min(lo, hi), max(lo, hi)
    return 'unknown', None, None


def clean_ocr_reference_artifacts(t: str) -> str:
    """
    Safely normalize OCR typo characters in reference context (Male/Female, inequalities).
    e.g. 'Mele: 55, Female: 38' -> 'Male: <55, Female: <38'
    """
    if not t:
        return ''
    # Normalize gender labels
    t = re.sub(r'(?i)\bmele\b', 'Male', t)
    t = re.sub(r'(?i)\bmsle\b', 'Male', t)
    t = re.sub(r'(?i)\bfe\s*mele\b', 'Female', t)
    
    # Fix OCR dropped decimal point specifically in Female Creatinine range: 'Female: 0.6-11' -> 'Female: 0.6-1.1'
    t = re.sub(r'(?i)(Female\s*[:\-]?\s*\d+\.\d+\s*-\s*)11(?!\.)\b', r'\g<1>1.1', t)
    
    # In reference context, corrupted characters preceding numbers represent inequalities
    # e.g. '? 90' -> '>= 90', '?55' / '55' / '*2' -> '<55' / '<2'
    t = re.sub(r'\?\s*(\d+(?:\.\d+)?)', r'>= \1', t)
    t = re.sub(r'[\ufffd\×\*]\s*(\d+(?:\.\d+)?)', r'<\1', t)
    
    # If Male: <X, Female: Y (where Female number has no operator in inequality context), infer operator
    m_ineq = re.search(r'Male\s*[:\-]?\s*([<≤>≥]=?)\s*\d+', t, re.IGNORECASE)
    if m_ineq:
        op = m_ineq.group(1)
        t = re.sub(r'(Female\s*[:\-]?\s*)(\d+(?:\.\d+)?)', rf'\g<1>{op}\2', t, flags=re.IGNORECASE)
        
    return t.strip()


def _expand_two_dot(match: re.Match) -> str:
    p1, mid, p3 = match.group(1), match.group(2), match.group(3)
    for k in range(1, len(mid)):
        d1, i2 = mid[:k], mid[k:]
        try:
            n1, n2 = float(f'{p1}.{d1}'), float(f'{i2}.{p3}')
            if n1 < n2:
                return f'{p1}.{d1} - {i2}.{p3}'
        except Exception:
            pass
    return match.group(0)


def reconstruct_fused_reference(text: str) -> str:
    """
    Safely reconstruct fused reference numbers when token belongs to reference column/row context.
    - Two-dot fused decimal ranges: '8.510.5' -> '8.5 - 10.5', '3.57.2' -> '3.5 - 7.2'
    - Fused 4-digit integers: '1540' -> '15 - 40'
    - Inequality prefix on single number: '*2' or '?2' -> '<2'
    """
    if not text:
        return ''
    s = text.strip()
    
    # 1. Fused decimal range with two dots (standalone or substring): e.g. '8.510.5' -> '8.5 - 10.5', '3.57.2' -> '3.5 - 7.2'
    s = re.sub(r'(\d+)\.(\d+)\.(\d+)', _expand_two_dot, s)

    # 2. Fused integers e.g. '1540' -> '15 - 40'
    m_4d = re.match(r'^(\d{2})(\d{2})$', s)
    if m_4d:
        n1, n2 = float(m_4d.group(1)), float(m_4d.group(2))
        if n1 < n2:
            return f'{int(n1)} - {int(n2)}'
            
    # 3. Asterisk/typo prefix on single number e.g. '*2' or '?2' -> '<2'
    m_star = re.match(r'^[\*?\ufffd]\s*(\d+(?:\.\d+)?)$', s)
    if m_star:
        return f'<{m_star.group(1)}'
        
    return s


def parse_report_reference(candidate: str) -> Optional[str]:
    if not candidate or not candidate.strip():
        return None
    cleaned_candidate = clean_ocr_reference_artifacts(candidate.strip())
    reconstructed = reconstruct_fused_reference(cleaned_candidate)
    ref_str, _src = extract_reference_range(reconstructed)
    if not ref_str:
        ref_str, _src = extract_reference_range(cleaned_candidate)
    if not ref_str:
        return None
    return clean_reference_string(ref_str)


def validate_report_reference(candidate: str, observed_value: Optional[float] = None, known_unit: Optional[str] = None) -> bool:
    if not candidate or not candidate.strip():
        return False
    ref_str = parse_report_reference(candidate)
    if not ref_str:
        return False
    if re.fullmatch(r'\d+(?:\.\d+)?', ref_str.strip()):
        return False
    if known_unit and candidate.strip().lower() == known_unit.strip().lower():
        return False
    return True


def resolve_reference(report_candidate: Optional[str], sita_fallback: Optional[str], observed_value: Optional[float] = None, known_unit: Optional[str] = None, biomarker_key: Optional[str] = None) -> ReferenceResolution:
    raw_candidate = report_candidate or ''
    if raw_candidate:
        if validate_report_reference(raw_candidate, observed_value, known_unit):
            ref_str = parse_report_reference(raw_candidate)
            if ref_str:
                ref_type, low, high = detect_reference_type(ref_str)
                if ref_type != 'unknown':
                    return ReferenceResolution(reference_range=ref_str, reference_source='report', reference_type=ref_type, low=low, high=high, is_gender_specific=(ref_type == 'gender_specific'), raw_report_candidate=raw_candidate)
    if sita_fallback and sita_fallback.strip():
        ref_type, low, high = detect_reference_type(sita_fallback.strip())
        if ref_type != 'unknown':
            return ReferenceResolution(reference_range=sita_fallback.strip(), reference_source='fallback', reference_type=ref_type, low=low, high=high, is_gender_specific=(ref_type == 'gender_specific'), raw_report_candidate=raw_candidate)
    return ReferenceResolution(reference_range='', reference_source='unknown', reference_type='unknown', low=None, high=None, is_gender_specific=False, raw_report_candidate=raw_candidate)


def build_structured_reference(resolution: ReferenceResolution) -> Dict[str, Any]:
    from app.services.status_engine import parse_structured_reference_range
    struct = parse_structured_reference_range(resolution.reference_range)
    struct['source'] = resolution.reference_source
    struct['type'] = resolution.reference_type
    struct['lower_limit'] = resolution.low
    struct['upper_limit'] = resolution.high
    return struct
