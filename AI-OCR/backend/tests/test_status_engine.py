import pytest
from app.services.status_engine import calculate_status, parse_reference_range_bounds


def test_parse_reference_range_bounds():
    assert parse_reference_range_bounds("12.5-16.0") == (12.5, 16.0)
    assert parse_reference_range_bounds("150 - 450") == (150.0, 450.0)
    assert parse_reference_range_bounds("(36-46)") == (36.0, 46.0)
    assert parse_reference_range_bounds("<200") == (None, 200.0)
    assert parse_reference_range_bounds("≤ 200") == (None, 200.0)
    assert parse_reference_range_bounds(">40") == (40.0, None)
    assert parse_reference_range_bounds("≥ 40") == (40.0, None)
    assert parse_reference_range_bounds("invalid text") == (None, None)
    assert parse_reference_range_bounds(None) == (None, None)


def test_calculate_status_normal():
    # Hemoglobin 12.6 vs 12.5-16
    res = calculate_status(12.6, "12.5-16.0")
    assert res["status"] == "Normal"
    assert res["lower_limit"] == 12.5
    assert res["upper_limit"] == 16.0
    assert "within" in res["status_reason"].lower()

    # WBC 6900 vs 4000-10500
    res_wbc = calculate_status(6900, "4000-10500")
    assert res_wbc["status"] == "Normal"


def test_calculate_status_low():
    # Hemoglobin 10.5 vs 12.5-16
    res_hb = calculate_status(10.5, "12.5-16.0")
    assert res_hb["status"] == "Low"
    assert res_hb["lower_limit"] == 12.5
    assert "below" in res_hb["status_reason"].lower()

    # Platelets 90 vs 150-450
    res_plt = calculate_status(90, "150-450")
    assert res_plt["status"] == "Low"


def test_calculate_status_high():
    # WBC 12000 vs 4000-10500
    res_wbc = calculate_status(12000, "4000-10500")
    assert res_wbc["status"] == "High"
    assert res_wbc["upper_limit"] == 10500
    assert "above" in res_wbc["status_reason"].lower()

    # Platelets 500 vs 150-450
    res_plt = calculate_status(500, "150-450")
    assert res_plt["status"] == "High"


def test_calculate_status_single_bounded():
    # < 200
    res_chol_normal = calculate_status(180, "< 200")
    assert res_chol_normal["status"] == "Normal"

    res_chol_high = calculate_status(250, "< 200")
    assert res_chol_high["status"] == "High"

    # > 40
    res_hdl_normal = calculate_status(50, "> 40")
    assert res_hdl_normal["status"] == "Normal"

    res_hdl_low = calculate_status(30, "> 40")
    assert res_hdl_low["status"] == "Low"


def test_calculate_status_unknown():
    res_none_val = calculate_status(None, "12.5-16.0")
    assert res_none_val["status"] == "Unknown"

    res_none_range = calculate_status(12.6, None)
    assert res_none_range["status"] == "Unknown"

    res_invalid_range = calculate_status(12.6, "N/A")
    assert res_invalid_range["status"] == "Unknown"
