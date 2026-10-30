import json
import os
import re
from typing import Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOSPITAL_TEMPLATES_PATH = os.path.join(BASE_DIR, "data", "hospital_templates.json")


def load_hospital_templates(path: str = HOSPITAL_TEMPLATES_PATH) -> Dict[str, Any]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def detect_hospital(ocr_text: str, templates: Dict[str, Any]) -> Tuple[str, float]:
    """
    Detect hospital template ID and confidence score from OCR text.
    """
    if not ocr_text:
        return "generic", 0.60

    ocr_lower = ocr_text.lower()

    for hosp_id, config in templates.items():
        if hosp_id == "generic":
            continue

        keywords = config.get("keywords", [])
        aliases = config.get("aliases", [])

        # Direct search for hospital keywords/aliases
        for kw in keywords + aliases:
            if kw and kw.lower() in ocr_lower:
                return hosp_id, 0.99

    return "generic", 0.60


def detect_report_category(ocr_text: str) -> Tuple[str, float]:
    """
    Detect lab report category (CBC, LIPID_PROFILE, THYROID_PROFILE, etc.) from OCR text.
    """
    if not ocr_text:
        return "UNKNOWN", 0.50

    ocr_lower = ocr_text.lower()

    # Priority keyword matching
    if any(k in ocr_lower for k in [
        "complete blood count", "cbc", "haematology report", "hemogram", "leucocyte count", "platelet count"
    ]):
        return "CBC", 0.95

    if any(k in ocr_lower for k in [
        "lipid profile", "cholesterol", "triglycerides", "hdl cholesterol", "ldl cholesterol"
    ]):
        return "LIPID_PROFILE", 0.95

    if any(k in ocr_lower for k in [
        "thyroid profile", "tsh", "thyroid stimulating hormone", "triiodothyronine", "thyroxine"
    ]):
        return "THYROID_PROFILE", 0.95

    if any(k in ocr_lower for k in [
        "liver function test", "lft", "sgpt", "sgot", "bilirubin", "alkaline phosphatase"
    ]):
        return "LIVER_FUNCTION_TEST", 0.95

    if any(k in ocr_lower for k in [
        "kidney function test", "kft", "renal function test", "rft", "serum creatinine", "blood urea"
    ]):
        return "KIDNEY_FUNCTION_TEST", 0.95

    if any(k in ocr_lower for k in [
        "hba1c", "glycated hemoglobin", "glycosylated hemoglobin", "fasting blood sugar", "diabetes profile"
    ]):
        return "DIABETES_PROFILE", 0.95

    if any(k in ocr_lower for k in [
        "vitamin profile", "vitamin d", "25-hydroxy", "vitamin b12", "cyanocobalamin"
    ]):
        return "VITAMIN_PROFILE", 0.95

    return "GENERIC", 0.50


def detect_report(ocr_text: str) -> Dict[str, Any]:
    """
    Step 1: Document Detector
    Detect hospital template and report category before parsing.
    """
    templates = load_hospital_templates()
    hospital_id, hosp_conf = detect_hospital(ocr_text, templates)
    category, cat_conf = detect_report_category(ocr_text)

    combined_confidence = round(max(hosp_conf, cat_conf), 2)

    return {
        "hospital": hospital_id,
        "report_type": category,
        "confidence": combined_confidence
    }
