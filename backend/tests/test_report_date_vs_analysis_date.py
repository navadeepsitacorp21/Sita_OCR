import pytest
from datetime import datetime, timezone
from app.utils.metadata_extractor import extract_laboratory_dates, normalize_date_string, extract_metadata
from app.services.trend_service import compute_biomarker_trends, get_effective_report_date
from app.database.models import HealthReport
from app.database.database import get_db, SessionLocal, engine, Base


def test_normalize_date_string_formats():
    assert normalize_date_string("07/11/2021", doc_context="Aster Clinics") == "07/11/2021"
    assert normalize_date_string("07)11/2021", doc_context="Aster Clinics") == "07/11/2021"
    assert normalize_date_string("2021-11-07") == "07/11/2021"
    assert normalize_date_string("2025-10-08") == "08/10/2025"
    assert normalize_date_string("08-Oct-2025") == "08/10/2025"
    assert normalize_date_string("07-Nov-2021") == "07/11/2021"
    assert normalize_date_string("Nov 07, 2021") == "07/11/2021"
    assert normalize_date_string("15.01.2022") == "15/01/2022"
    assert normalize_date_string(None) is None
    assert normalize_date_string("") is None


def test_ambiguous_numeric_date_not_guessed():
    """
    PHASE 2.1.1 Requirement 1:
    A genuinely ambiguous numeric date such as 03/04/2021 without reliable document context
    must not be guessed and must return None. Also invalid dates like 31/02/2021 return None.
    """
    assert normalize_date_string("03/04/2021") is None
    assert normalize_date_string("31/02/2021") is None
    
    # Document with ambiguous date and no context
    ambig_text = "Patient Report\nDate: 03/04/2021\nResult: 10.5"
    dates = extract_laboratory_dates(ambig_text)
    assert dates["report_date"] is None


def test_aster_cbc_date_continues_to_resolve():
    """
    PHASE 2.1.1 Requirement 2:
    The existing Aster CBC date 07/11/2021 continues to resolve correctly as 07 Nov 2021.
    """
    aster_text = """
    Aster CLINIC
    Cellected On: 07)11/2021 13:38
    Reported On: 07/11/2021 17:39
    """
    dates = extract_laboratory_dates(aster_text)
    assert dates["report_date"] == "07/11/2021"
    assert dates["collection_date"] == "07/11/2021"


def test_extract_laboratory_dates_preserves_semantics():
    sample_text = """
    Aster Clinics & Hospital
    Ordered On: 05/11/2021 10:00
    Collected On: 07)11/2021 13:38
    Received On: 07/11/2021 17:27
    Reported On: 08/11/2021 09:15
    """
    dates = extract_laboratory_dates(sample_text)
    assert dates["ordered_date"] == "05/11/2021"
    assert dates["collection_date"] == "07/11/2021"
    assert dates["received_date"] == "07/11/2021"
    assert dates["reported_date"] == "08/11/2021"
    # Collection date takes precedence as clinical report date
    assert dates["report_date"] == "07/11/2021"


def test_missing_report_date_returns_none_without_hallucinating():
    sample_no_date = """
    Patient Name: Test User
    Age: 45
    Gender: Male
    Test: Complete Blood Count
    Hemoglobin 14.5 g/dL
    """
    dates = extract_laboratory_dates(sample_no_date)
    assert dates["report_date"] is None
    assert dates["collection_date"] is None
    assert dates["reported_date"] is None

    meta = extract_metadata(sample_no_date)
    assert meta["report"]["report_date"] is None
    assert meta["report"]["collection_date"] is None


def test_trend_ordering_uses_medical_report_date_over_upload_date():
    """
    Validates Requirement 7:
    Report A: Collection Date 07 Nov 2021, Uploaded/Analyzed 23 Oct 2026
    Report B: Collection Date 15 Jan 2022, Uploaded/Analyzed 23 Oct 2026 (uploaded slightly earlier or later)
    The trend chronology must recognize 07 Nov 2021 -> 15 Jan 2022 -> current.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Create Report A (older clinical date: 2021-11-07, but uploaded today)
        rep_a = HealthReport(
            report_id="test_rep_2021",
            report_type="CBC_TREND_TEST",
            uploaded_at=datetime(2026, 10, 23, 10, 0, 0, tzinfo=timezone.utc),
            filename="Screenshot_2021.png",
            report_json={
                "report_date": "07/11/2021",
                "parsed_report": {
                    "biomarkers": [
                        {"key": "hemoglobin", "value": 13.0, "unit": "g/dL", "status": "Normal"}
                    ]
                }
            }
        )

        # Create Report B (newer clinical date: 2022-01-15, uploaded at the exact same or slightly different time)
        rep_b = HealthReport(
            report_id="test_rep_2022",
            report_type="CBC_TREND_TEST",
            uploaded_at=datetime(2026, 10, 23, 9, 0, 0, tzinfo=timezone.utc),
            filename="Screenshot_2022.png",
            report_json={
                "report_date": "15/01/2022",
                "parsed_report": {
                    "biomarkers": [
                        {"key": "hemoglobin", "value": 14.0, "unit": "g/dL", "status": "Normal"}
                    ]
                }
            }
        )

        db.add(rep_a)
        db.add(rep_b)
        db.commit()

        # Current report being analyzed today with Hemoglobin = 15.0
        current_bms = [{"key": "hemoglobin", "name": "Hemoglobin", "value": 15.0, "unit": "g/dL"}]

        trends = compute_biomarker_trends(db, current_bms, "CBC_TREND_TEST", exclude_report_id="current_rep")

        assert "hemoglobin" in trends
        hb_trend = trends["hemoglobin"]

        # The immediate previous report chronologically is Report B (Jan 2022), NOT Report A (Nov 2021)
        # Even though rep_a had a later uploaded_at timestamp (10:00 vs 09:00)!
        assert hb_trend["previous_value"] == 14.0
        assert hb_trend["previous_date"] == "15/01/2022"
        assert hb_trend["diff"] == 1.0
        assert hb_trend["direction"] == "increased"

        # Multi-report progression: 13.0 (Nov 2021) -> 14.0 (Jan 2022) -> 15.0 (Today)
        assert hb_trend["multi_report_trend"] is not None
        assert "consistently increased" in hb_trend["multi_report_trend"]

    finally:
        db.query(HealthReport).filter(HealthReport.report_id.in_(["test_rep_2021", "test_rep_2022"])).delete()
        db.commit()
        db.close()
