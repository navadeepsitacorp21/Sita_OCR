import os
import pytest
from app.utils.metadata_extractor import extract_metadata, extract_patient_gender, extract_patient_age

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_metadata_extraction_lft_complete():
    text = read_fixture("lft_complete.txt")
    meta = extract_metadata(text)

    patient = meta["patient"]
    assert patient["gender"] == "male"
    assert patient["age"] == 25
    assert patient["name"] == "Aarav Mehra"
    assert patient["patient_id"] == "NPD/2025/0006"

    report = meta["report"]
    assert report["report_date"] == "08-Oct-2025"

    hospital = meta["hospital"]
    assert "care diagnostics" in hospital["name"].lower()


def test_gender_extraction_shorthand():
    assert extract_patient_gender("Age/Sex: 32 Y / Female") == "female"
    assert extract_patient_gender("Gender : M") == "male"
    assert extract_patient_gender("Sex: F") == "female"
    assert extract_patient_gender("Unknown header") == "unknown"


def test_age_extraction_variations():
    assert extract_patient_age("Age: 45 Yrs") == 45
    assert extract_patient_age("30 Y / Male") == 30
    assert extract_patient_age("Age / Sex : 28 / Female") == 28
