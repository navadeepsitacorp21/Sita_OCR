from typing import Dict, Any


def calculate_tripart_confidence(
    ocr_confidence: float = 1.0,
    alias_priority: int = 80,
    value_source: str = "same_line",
    reference_source: str = "report",
    validation_status: str = "passed",
    is_unit_normalized: bool = False,
    multiple_candidates: bool = False
) -> Dict[str, Any]:
    """
    Step 7: Tri-part Confidence Engine
    Calculates detailed ocr, parser, and validation confidence scores per biomarker.
    """
    ocr_score = max(0.0, min(1.0, float(ocr_confidence)))

    parser_score = 1.0
    if value_source in ["next_line", "lookahead", "inferred"]:
        parser_score -= 0.05
    if reference_source == "fallback":
        parser_score -= 0.05
    if alias_priority < 80:
        parser_score -= 0.05
    if is_unit_normalized:
        parser_score -= 0.05
    if multiple_candidates:
        parser_score -= 0.05
    parser_score = max(0.50, round(parser_score, 2))

    if validation_status == "passed":
        validation_score = 1.00
    elif validation_status == "repaired":
        validation_score = 0.70
    else:
        validation_score = 0.00

    overall_confidence = max(0.50, round((ocr_score * 0.4) + (parser_score * 0.4) + (validation_score * 0.2), 2))

    return {
        "confidence": {
            "ocr": round(ocr_score, 2),
            "parser": parser_score,
            "validation": round(validation_score, 2)
        },
        "overall_confidence": overall_confidence
    }
