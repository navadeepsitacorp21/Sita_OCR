import pytest
from app.services.parser_service import (
    parse_vitamin_profile_report,
    parse_cbc_report,
    parse_kidney_function_test_report,
    parse_liver_function_test_report,
    parse_thyroid_profile_report
)
from app.utils.ocr_noise_filter import is_metadata_line, is_report_title_line, clean_line_from_metadata


def test_metadata_line_detection():
    assert is_metadata_line("PATIENT ID : PK22638485") is True
    assert is_metadata_line("UHID: 100984832") is True
    assert is_metadata_line("REPORT ID : MH20230088") is True
    assert is_metadata_line("DOB: 12/04/1985 Age / Sex: 38 Y / M") is True
    assert is_metadata_line("HOME COLLECTION PHONE: 9876543210") is True
    assert is_metadata_line("SAMPLE COLLECTED ON: 24/06/2023 09:12:00") is True
    assert is_metadata_line("METHOD: ECLIA TECHNOLOGY") is True
    assert is_metadata_line("Page 1 of 3") is True
    assert is_metadata_line("*** END OF REPORT ***") is True

    # Valid biomarker rows should not be flagged as metadata
    assert is_metadata_line("25-OH Vitamin D 12.17 ng/mL 30-100") is False
    assert is_metadata_line("Serum Creatinine 1.01 mg/dL 0.6-1.3") is False


def test_report_title_rejection():
    assert is_report_title_line("TEST NAME : VITAMIN D PROFILE") is True
    assert is_report_title_line("VITAMIN PROFILE") is True
    assert is_report_title_line("THYROID PROFILE") is True
    assert is_report_title_line("LIPID PROFILE") is True
    assert is_report_title_line("Investigation Observed Value Unit Reference Interval") is True

    # Real biomarker row is not a title
    assert is_report_title_line("Vitamin D Total 12.17 ng/mL") is False


def test_clean_line_from_metadata():
    # Dates, timestamps, phone numbers, alphanumeric IDs
    line = "Vitamin D Total PK22638485 12.17 ng/mL 24/06/2023 09:12 30-100"
    cleaned = clean_line_from_metadata(line)
    assert "PK22638485" not in cleaned
    assert "24/06/2023" not in cleaned
    assert "09:12" not in cleaned
    assert "12.17" in cleaned
    assert "30-100" in cleaned


def test_thyrocare_vitamin_d_with_patient_id_and_barcode():
    text = """
    PATIENT ID : PK22638485
    BARCODE : 9876543210
    SAMPLE COLLECTED ON : 24/06/2023 09:12
    TEST NAME : VITAMIN D PROFILE
    25-OH Vitamin D Total 12.17 ng/mL 30-100
    METHOD : CMIA
    *** END OF REPORT ***
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "vitamin_d"
    assert bm["value"] == 12.17
    assert bm["unit"] == "ng/mL"
    assert bm["status"] == "Low"
    assert bm["reference_range"] == "30-100"
    assert bm["value_source"] == "same_line"
    assert bm["value_validation"] == "passed"
    assert bm["context_match"] is True


def test_multi_line_vitamin_d():
    text = """
    PATIENT ID : 99823485
    Vitamin D Total
    12.17 ng/mL
    30-100
    """
    parsed = parse_vitamin_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "vitamin_d"
    assert bm["value"] == 12.17
    assert bm["unit"] == "ng/mL"
    assert bm["value_source"] == "next_line"
    assert bm["status"] == "Low"


def test_cbc_platelets_raw_count_not_confused():
    text = """
    PATIENT ID: 1234567890
    Platelet Count 300000 /cumm 150000-410000
    """
    parsed = parse_cbc_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "platelet_count"
    assert bm["display_value"] == 300000.0
    assert bm["canonical_value"] == 300.0
    assert bm["status"] == "Normal"


def test_kidney_creatinine_row_with_patient_metadata():
    text = """
    UHID: 10023489
    REGISTRATION NO: 9948281
    Serum Creatinine 1.01 mg/dL 0.6-1.3
    PHONE: 9848022338
    """
    parsed = parse_kidney_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "serum_creatinine"
    assert bm["value"] == 1.01
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "Normal"


def test_liver_bilirubin_row_with_dates():
    text = """
    COLLECTED ON: 15/09/2026 10:30
    Total Bilirubin 0.8 mg/dL 0.2-1.2
    REPORTED ON: 15/09/2026 14:45
    """
    parsed = parse_liver_function_test_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "total_bilirubin"
    assert bm["value"] == 0.8
    assert bm["unit"] == "mg/dL"
    assert bm["status"] == "Normal"


def test_thyroid_tsh_row_with_qr_code_number():
    text = """
    QR CODE : 849204928194
    TSH 2.45 µIU/mL 0.45-4.5
    """
    parsed = parse_thyroid_profile_report(text)
    assert parsed["biomarkers_found"] == 1
    bm = parsed["biomarkers"][0]
    assert bm["key"] == "tsh"
    assert bm["value"] == 2.45
    assert bm["unit"] == "µIU/mL"
    assert bm["status"] == "Normal"


def test_extreme_id_number_rejected_for_vitamin():
    # If an OCR error placed an ID on the same line as a biomarker without valid measurement
    text = "Vitamin D 2638485"
    parsed = parse_vitamin_profile_report(text)
    # Biological validation rejects 2638485 for Vitamin D (max threshold 300)
    assert parsed["biomarkers_found"] == 0
