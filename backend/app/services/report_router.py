from typing import Dict, Any, List, Optional
from app.services.parser_service import (
    parse_cbc_report,
    parse_lipid_profile_report,
    parse_diabetes_profile_report,
    parse_thyroid_profile_report,
    parse_liver_function_test_report,
    parse_kidney_function_test_report,
    parse_vitamin_profile_report
)

SUPPORTED_REPORT_TYPES = [
    "CBC",
    "LIPID_PROFILE",
    "DIABETES_PROFILE",
    "THYROID_PROFILE",
    "LIVER_FUNCTION_TEST",
    "KIDNEY_FUNCTION_TEST",
    "VITAMIN_PROFILE"
]

KNOWN_UNSUPPORTED_TYPES = []


def route_report_parser(
    report_type: str,
    ocr_text: str,
    ocr_lines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Route recognized report category to its respective parser.
    Returns parsed structured report or descriptive placeholder for unhandled types.
    """
    if report_type == "CBC":
        return parse_cbc_report(ocr_text, ocr_lines=ocr_lines)

    if report_type == "LIPID_PROFILE":
        return parse_lipid_profile_report(ocr_text, ocr_lines=ocr_lines)

    if report_type == "DIABETES_PROFILE":
        return parse_diabetes_profile_report(ocr_text, ocr_lines=ocr_lines)

    if report_type == "THYROID_PROFILE":
        return parse_thyroid_profile_report(ocr_text, ocr_lines=ocr_lines)

    if report_type == "LIVER_FUNCTION_TEST":
        return parse_liver_function_test_report(ocr_text, ocr_lines=ocr_lines)

    if report_type == "KIDNEY_FUNCTION_TEST":
        return parse_kidney_function_test_report(ocr_text, ocr_lines=ocr_lines)

    if report_type == "VITAMIN_PROFILE":
        return parse_vitamin_profile_report(ocr_text, ocr_lines=ocr_lines)

    if report_type in KNOWN_UNSUPPORTED_TYPES:
        return {
            "report_type": report_type,
            "status": "parser_not_implemented",
            "message": f"Parser for {report_type} will be available in a future Health Vault update.",
            "supported_report_types": SUPPORTED_REPORT_TYPES,
            "biomarkers": []
        }

    return {
        "report_type": "UNKNOWN",
        "status": "unknown_report_type",
        "message": "This document could not be identified as a supported laboratory report.",
        "supported_report_types": SUPPORTED_REPORT_TYPES,
        "biomarkers": []
    }
