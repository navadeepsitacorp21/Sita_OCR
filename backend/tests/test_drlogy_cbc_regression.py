import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.metadata_extractor import (
    normalize_date_string,
    extract_laboratory_dates,
    extract_report_interpretation,
    clean_interpretation_text,
    extract_metadata
)
from app.parsers.cbc_parser import CBCParser
from app.services.medical_rule_engine import detect_cross_biomarker_patterns
from app.services.medical_explanation_engine import (
    generate_medical_explanation,
    generate_pattern_explanation,
    generate_doctor_discussion_points
)

client = TestClient(app)

FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures",
    "ocr",
    "drlogy_cbc_report.webp"
)


class TestDrlogyDateExtraction:
    """Test date parsing and OCR noise normalization for laboratory dates."""

    @pytest.mark.parametrize("raw_date, expected", [
        ("02 Dec, 2022", "02/12/2022"),
        ("02Dec,2022", "02/12/2022"),
        ("02 Dec 2022", "02/12/2022"),
        ("02Dec2022", "02/12/2022"),
        ("02 Dec, 22", "02/12/2022"),
        ("02Dec,22", "02/12/2022"),
        ("02 Dec 2X", "02/12/2022"),
        ("02Dec2X", "02/12/2022"),
        ("02 Dec, 202X", "02/12/2022"),
    ])
    def test_date_variations_normalized(self, raw_date, expected):
        norm = normalize_date_string(raw_date)
        assert norm == expected, f"Failed for {raw_date}: got {norm}"

    @pytest.mark.parametrize("ambiguous_date", [
        "02 Dec XX",
        "02 Dec",
        "Dec 2022",
        "invalid-date",
        "",
        None,
    ])
    def test_ambiguous_dates_not_guessed(self, ambiguous_date):
        assert normalize_date_string(ambiguous_date) is None

    def test_extract_laboratory_dates_from_ocr_text(self):
        sample_text = """
        Drlogy Pathology Lab
        Collected on : 03:11 PM 02 Dec, 2X
        Reported on : 04:35 PM 02 Dec, 2X
        Generated on : 02 Dec, 202X 05:00 PM
        """
        dates = extract_laboratory_dates(sample_text)
        assert dates["collection_date"] == "02/12/2022"
        assert dates["reported_date"] == "02/12/2022"
        assert dates["report_date"] == "02/12/2022"


class TestReportInterpretationExtraction:
    """Test verbatim extraction of free-text laboratory notes."""

    def test_clean_interpretation_text(self):
        cleaned = clean_interpretation_text("Furtherconfirmfor Anemia")
        assert cleaned == "Further confirm for Anemia"

    def test_extract_report_interpretation(self):
        sample_text = """
        Instruments: Fully automated cell counter-Mindray 300
        Interpretation: Furtherconfirmfor Anemia
        Thanks for Reference
        """
        interp = extract_report_interpretation(sample_text)
        assert interp is not None
        assert interp["text"] == "Further confirm for Anemia"
        assert interp["source"] == "report"

    def test_extract_metadata_includes_interpretation(self):
        sample_text = """
        Drlogy Pathology Lab
        Age: 27 Years / Male
        Collected on: 03:11 PM 02 Dec, 2X
        Interpretation: Furtherconfirmfor Anemia
        """
        meta = extract_metadata(sample_text)
        assert meta["report"]["report_date"] == "02/12/2022"
        assert meta["report_interpretation"] == {
            "text": "Further confirm for Anemia",
            "source": "report"
        }


class TestNonDiagnosticPatternLanguage:
    """Verify strictly non-diagnostic pattern wording and explanation generation."""

    def test_anemia_pattern_summary_non_diagnostic(self):
        biomarkers = [
            {"key": "hemoglobin", "name": "Hemoglobin", "status": "low", "value": 8.5, "unit": "g/dL"},
            {"key": "pcv", "name": "Hematocrit", "status": "high", "value": 57.5, "unit": "%"},
            {"key": "mcv", "name": "MCV", "status": "normal", "value": 87.75, "unit": "fL"},
        ]
        patterns = detect_cross_biomarker_patterns(biomarkers, report_type="CBC")
        anemia_pat = next((p for p in patterns if p.get("pattern_id") == "anemia_pattern"), None)
        assert anemia_pat is not None
        # Must NOT diagnose "You have anemia"
        assert "you have anemia" not in anemia_pat["summary"].lower()
        assert "you have anemia" not in anemia_pat["name"].lower()
        # Must use non-diagnostic observational language
        assert "a low hemoglobin result was observed" in anemia_pat["summary"].lower()

    def test_pattern_explanation_references_report_note(self):
        biomarkers = [
            {"key": "hemoglobin", "name": "Hemoglobin", "status": "low", "value": 8.5, "unit": "g/dL"},
        ]
        patterns = detect_cross_biomarker_patterns(biomarkers, report_type="CBC")
        report_interp = {"text": "Further confirm for Anemia", "source": "report"}
        exp = generate_pattern_explanation(patterns, report_interpretation=report_interp)
        assert len(exp) > 0
        exp_text = exp[0]["explanation"]
        assert "Further confirm for Anemia" in exp_text
        assert "Laboratory report note" in exp_text
        assert "you have anemia" not in exp_text.lower()

    def test_doctor_discussion_points_includes_lab_note(self):
        biomarkers = [
            {"key": "hemoglobin", "name": "Hemoglobin", "status": "low", "value": 8.5, "unit": "g/dL"},
        ]
        report_interp = {"text": "Further confirm for Anemia", "source": "report"}
        points = generate_doctor_discussion_points(
            biomarkers=biomarkers,
            report_interpretation=report_interp
        )
        assert any("Further confirm for Anemia" in p for p in points)


class TestDrlogyCBCFixtureExtraction:
    """Test full parsing and biomarker extraction on the Drlogy CBC report fixture."""

    @pytest.mark.skipif(not os.path.exists(FIXTURE_PATH), reason="Drlogy CBC fixture not found")
    def test_drlogy_cbc_report_parsing_and_isolation(self):
        with open(FIXTURE_PATH, "rb") as f:
            file_bytes = f.read()

        response = client.post(
            "/api/v1/medical-reports/analyze",
            files={"file": ("drlogy_cbc_report.webp", file_bytes, "image/webp")},
            data={"patient_gender": "male"}
        )
        assert response.status_code == 200, f"Analysis failed: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert data["report_type"] == "CBC"
        assert data["report_date"] == "02/12/2022"

        # Report interpretation captured as source metadata
        assert data.get("report_interpretation") is not None
        assert data["report_interpretation"]["text"] == "Further confirm for Anemia"
        assert data["report_interpretation"]["source"] == "report"

        # Check extracted biomarkers
        bms = {bm["key"]: bm for bm in data["biomarkers"]}
        expected_keys = {"hemoglobin", "pcv", "mcv", "mch", "mchc", "rdw", "platelet_count"}
        for k in expected_keys:
            assert k in bms, f"Expected CBC parameter '{k}' not found in extracted biomarkers: {list(bms.keys())}"

        # Total recognized biomarkers should be 7
        assert len(bms) == 7

        # Verify values and reference ranges
        hb = bms["hemoglobin"]
        assert hb["value"] == 8.5
        assert hb["status"].lower() == "low"
        assert "13" in hb["reference_range"]

        pcv = bms["pcv"]
        assert pcv["value"] == 57.5
        assert pcv["status"].lower() == "high"

        mcv = bms["mcv"]
        assert mcv["value"] == 87.75
        assert mcv["status"].lower() == "normal"

        mch = bms["mch"]
        assert mch["value"] == 27.2
        assert mch["status"].lower() == "normal"

        mchc = bms["mchc"]
        assert mchc["value"] == 32.8
        assert mchc["status"].lower() == "normal"

        rdw = bms["rdw"]
        assert rdw["value"] == 13.6
        assert rdw["status"].lower() == "normal"

        plt = bms["platelet_count"]
        # Canonical value for platelet_count (150,000 cumm = 150.0 10^3/uL)
        assert plt["value"] in (150.0, 150000.0)
        assert plt["status"].lower() == "normal"

        # Contaminated / non-CBC rows must NOT be in biomarkers
        unwanted_keys = [
            "body_temperature", "body_weight", "sodium", "potassium",
            "calcium", "vitamin_b12", "chloride", "total_protein"
        ]
        for uw in unwanted_keys:
            assert uw not in bms, f"Contaminated non-CBC key '{uw}' should not be in CBC result set"
