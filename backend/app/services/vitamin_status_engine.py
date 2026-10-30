from typing import Dict, Any, Optional, Tuple
import re


def classify_vitamin_d_stage(value: Optional[float]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Deterministically classify Vitamin D levels according to standard clinical ranges:
    - < 20 ng/mL    : Deficiency (Status: Low)
    - 20 - 30 ng/mL : Insufficiency (Status: Low)
    - 30 - 100 ng/mL: Sufficiency (Status: Normal)
    - > 100 ng/mL   : Toxicity (Status: High)

    Returns:
        (clinical_stage, clinical_message, status)
    """
    if value is None:
        return None, None, None

    val = float(value)
    if val < 20.0:
        stage = "Deficiency"
        message = "Vitamin D level indicates deficiency."
        status = "Low"
    elif 20.0 <= val < 30.0:
        stage = "Insufficiency"
        message = "Vitamin D level indicates insufficiency."
        status = "Low"
    elif 30.0 <= val <= 100.0:
        stage = "Sufficiency"
        message = "Vitamin D level is sufficient."
        status = "Normal"
    else:  # val > 100.0
        stage = "Toxicity"
        message = "Vitamin D level indicates potential toxicity."
        status = "High"

    return stage, message, status


def extract_vitamin_d_interpretation_ranges(text: str) -> Optional[Dict[str, str]]:
    """
    Extracts structured Vitamin D clinical interpretation ranges from text if present.
    Example text:
        Deficiency : <20 ng/mL
        Insufficiency : 20-30 ng/mL
        Sufficiency : 30-100 ng/mL
        Toxicity : >100 ng/mL
    
    Returns:
        Dict with keys "deficiency", "insufficiency", "sufficiency", "toxicity" or None.
    """
    if not text:
        return None

    ranges = {}

    deficiency_match = re.search(r'\bDeficiency\s*[:\-]?\s*([<≤]?\s*\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if deficiency_match:
        val = deficiency_match.group(1).replace(" ", "")
        ranges["deficiency"] = val if val.startswith("<") or val.startswith("≤") else f"<{val}"

    insufficiency_match = re.search(r'\bInsufficiency\s*[:\-]?\s*(\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if insufficiency_match:
        ranges["insufficiency"] = re.sub(r'\s+', '', insufficiency_match.group(1).replace("–", "-"))

    sufficiency_match = re.search(r'\bSufficiency\s*[:\-]?\s*(\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if sufficiency_match:
        ranges["sufficiency"] = re.sub(r'\s+', '', sufficiency_match.group(1).replace("–", "-"))

    toxicity_match = re.search(r'\bToxicity\s*[:\-]?\s*([>≥]?\s*\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if toxicity_match:
        val = toxicity_match.group(1).replace(" ", "")
        ranges["toxicity"] = val if val.startswith(">") or val.startswith("≥") else f">{val}"

    # If at least 2 ranges were found, consider it a rich clinical range table
    if len(ranges) >= 2:
        # Fill standard defaults if any individual key was missed in OCR scan
        if "deficiency" not in ranges:
            ranges["deficiency"] = "<20"
        if "insufficiency" not in ranges:
            ranges["insufficiency"] = "20-30"
        if "sufficiency" not in ranges:
            ranges["sufficiency"] = "30-100"
        if "toxicity" not in ranges:
            ranges["toxicity"] = ">100"
        return ranges

    return None
