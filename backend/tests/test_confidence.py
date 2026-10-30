import pytest
from app.utils.confidence import calculate_tripart_confidence


def test_confidence_calculation_perfect():
    res = calculate_tripart_confidence(
        ocr_confidence=0.98,
        alias_priority=100,
        value_source="same_line",
        reference_source="report",
        validation_status="passed"
    )
    conf = res["confidence"]
    assert conf["ocr"] == 0.98
    assert conf["parser"] == 1.0
    assert conf["validation"] == 1.0
    assert res["overall_confidence"] >= 0.90


def test_confidence_calculation_reduced():
    res = calculate_tripart_confidence(
        ocr_confidence=0.85,
        alias_priority=50,
        value_source="next_line",
        reference_source="fallback",
        validation_status="repaired"
    )
    conf = res["confidence"]
    assert conf["ocr"] == 0.85
    assert conf["parser"] < 1.0
    assert conf["validation"] == 0.70
