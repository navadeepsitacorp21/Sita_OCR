import pytest
from app.utils.unit_normalizer import normalize_biomarker_value
from app.services.status_engine import calculate_status, parse_reference_range_bounds
from app.services.parser_service import parse_cbc_report


def test_platelet_unit_normalization():
    # Platelet count reported in /cumm
    norm = normalize_biomarker_value(
        key="platelet_count",
        value=300000.0,
        unit="/cumm",
        reference_range="150000-410000",
        raw_text="Platelet Count 300000 /cumm 150000-410000"
    )
    assert norm["original_value"] == 300000.0
    assert norm["original_unit"] == "/cumm"
    assert norm["value"] == 300.0
    assert norm["unit"] == "10^3/μL"
    assert norm["reference_range"] == "150-410"
    assert norm["conversion_applied"] is True
    assert "Normalized platelet count" in norm["conversion_reason"]

    # Verify status calculation with normalized values
    status_info = calculate_status(norm["value"], norm["reference_range"])
    assert status_info["status"] == "Normal"


def test_rbc_unit_normalization():
    norm = normalize_biomarker_value(
        key="rbc_count",
        value=4500000.0,
        unit="/cumm",
        reference_range="4000000-5500000"
    )
    assert norm["original_value"] == 4500000.0
    assert norm["value"] == 4.5
    assert norm["unit"] == "10^6/μL"
    assert norm["reference_range"] == "4-5.5"
    assert norm["conversion_applied"] is True

    status_info = calculate_status(norm["value"], norm["reference_range"])
    assert status_info["status"] == "Normal"


def test_wbc_unit_normalization():
    norm = normalize_biomarker_value(
        key="wbc_count",
        value=7.5,
        unit="10^3/μL",
        reference_range="4.0-11.0"
    )
    assert norm["original_value"] == 7.5
    assert norm["value"] == 7500.0
    assert norm["unit"] == "cells/cu.mm"
    assert norm["reference_range"] == "4000-11000"
    assert norm["conversion_applied"] is True

    status_info = calculate_status(norm["value"], norm["reference_range"])
    assert status_info["status"] == "Normal"


def test_hemoglobin_unit_normalization():
    norm = normalize_biomarker_value(
        key="hemoglobin",
        value=135.0,
        unit="g/L",
        reference_range="125-160"
    )
    assert norm["original_value"] == 135.0
    assert norm["value"] == 13.5
    assert norm["unit"] == "gm/dL"
    assert norm["reference_range"] == "12.5-16"
    assert norm["conversion_applied"] is True

    status_info = calculate_status(norm["value"], norm["reference_range"])
    assert status_info["status"] == "Normal"


def test_report_reference_overrides_fallback():
    # Report where Monocytes reference interval is printed as 2-10 (fallback is 2-8)
    text = "Monocytes 5.0 % 2 - 10"
    parsed = parse_cbc_report(text)
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "monocytes"
    assert bm["reference_source"] == "report"
    assert "2" in bm["reference_range"] and "10" in bm["reference_range"]
    assert bm["status"] == "Normal"

    # Report without printed reference range should use fallback
    no_ref_text = "Monocytes 5.0 %"
    parsed_no_ref = parse_cbc_report(no_ref_text)
    bm_fallback = parsed_no_ref["biomarkers"][0]
    assert bm_fallback["reference_source"] == "fallback"
    assert bm_fallback["reference_range"] == "2-8"
    assert bm_fallback["status"] == "Normal"


def test_boundary_comparisons_inclusive():
    # Inclusive dual bounded range
    res_lower = calculate_status(20.0, "20-40")
    assert res_lower["status"] == "Normal"

    res_upper = calculate_status(40.0, "20-40")
    assert res_upper["status"] == "Normal"

    # Strict vs non-strict greater than
    res_strict_gt_equal = calculate_status(40.0, ">40")
    assert res_strict_gt_equal["status"] == "Low"

    res_strict_gt_above = calculate_status(41.0, ">40")
    assert res_strict_gt_above["status"] == "Normal"

    res_non_strict_gt = calculate_status(40.0, ">=40")
    assert res_non_strict_gt["status"] == "Normal"

    res_non_strict_gt_low = calculate_status(39.0, ">=40")
    assert res_non_strict_gt_low["status"] == "Low"

    # Strict vs non-strict less than
    res_strict_lt_equal = calculate_status(200.0, "<200")
    assert res_strict_lt_equal["status"] == "High"

    res_strict_lt_below = calculate_status(199.0, "<200")
    assert res_strict_lt_below["status"] == "Normal"

    res_non_strict_lt = calculate_status(200.0, "<=200")
    assert res_non_strict_lt["status"] == "Normal"

    res_non_strict_lt_high = calculate_status(201.0, "<=200")
    assert res_non_strict_lt_high["status"] == "High"


def test_parenthesized_range_parsing():
    bounds = parse_reference_range_bounds("(36-46)")
    assert bounds == (36.0, 46.0)

    res = calculate_status(38.0, "(36-46)")
    assert res["status"] == "Normal"
    assert res["lower_limit"] == 36.0
    assert res["upper_limit"] == 46.0
