import pytest
from app.services.parser_service import parse_vitamin_profile_report
from app.services.health_summary_service import generate_health_summary
from app.services.health_highlights_service import generate_health_highlights
from app.services.vitamin_status_engine import classify_vitamin_d_stage, extract_vitamin_d_interpretation_ranges
from app.services.biomarker_family_service import group_primary_biomarkers


SAMPLE_THYROCARE_VITAMIN_PANEL = """
THYROCARE LABORATORIES
VITAMIN PROFILE
25-OH VITAMIN D TOTAL : 12.17 ng/mL
VITAMIN D2            : 1.15  ng/mL
VITAMIN D3            : 11.02 ng/mL

Interpretation Range:
Deficiency : <20 ng/mL
Insufficiency : 20-30 ng/mL
Sufficiency : 30-100 ng/mL
Toxicity : >100 ng/mL
"""


def test_thyrocare_vitamin_d_total_with_d2_and_d3():
    """
    Case 1: Vitamin D Total + D2 + D3 present together with rich interpretation ranges.
    """
    parsed = parse_vitamin_profile_report(SAMPLE_THYROCARE_VITAMIN_PANEL)
    assert parsed["parse_status"] == "success"

    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    assert "vitamin_d" in bm_map
    assert "vitamin_d2" in bm_map
    assert "vitamin_d3" in bm_map

    vit_d = bm_map["vitamin_d"]
    assert vit_d["value"] == 12.17
    assert vit_d["unit"] == "ng/mL"
    assert vit_d["is_primary"] is True
    assert vit_d["family"] == "vitamin_d_family"
    assert vit_d["clinical_stage"] == "Deficiency"
    assert vit_d["reference_source"] == "report"
    assert vit_d["clinical_ranges"]["deficiency"] == "<20"
    assert vit_d["clinical_ranges"]["toxicity"] == ">100"

    vit_d2 = bm_map["vitamin_d2"]
    assert vit_d2["value"] == 1.15
    assert vit_d2["is_primary"] is False
    assert vit_d2["family"] == "vitamin_d_family"

    vit_d3 = bm_map["vitamin_d3"]
    assert vit_d3["value"] == 11.02
    assert vit_d3["is_primary"] is False
    assert vit_d3["family"] == "vitamin_d_family"


def test_only_vitamin_d_total():
    """
    Case 2: Only Vitamin D Total present.
    """
    text = "Vitamin D Total 45.0 ng/mL (30-100)"
    parsed = parse_vitamin_profile_report(text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    
    assert "vitamin_d" in bm_map
    assert bm_map["vitamin_d"]["value"] == 45.0
    assert bm_map["vitamin_d"]["clinical_stage"] == "Sufficiency"
    assert bm_map["vitamin_d"]["status"] == "Normal"
    assert "vitamin_d2" not in bm_map
    assert "vitamin_d3" not in bm_map


def test_only_vitamin_d3():
    """
    Case 3: Only Vitamin D3 present.
    """
    text = "Vitamin D3 18.0 ng/mL (30-100)"
    parsed = parse_vitamin_profile_report(text)
    bm_map = {b["key"]: b for b in parsed["biomarkers"]}
    
    assert "vitamin_d" in bm_map
    assert bm_map["vitamin_d"]["value"] == 18.0
    assert bm_map["vitamin_d"]["clinical_stage"] == "Deficiency"
    assert bm_map["vitamin_d"]["status"] == "Low"


def test_vitamin_d_toxicity_stage():
    """
    Case 4: Vitamin D Toxicity (>100 ng/mL).
    """
    stage, msg, status = classify_vitamin_d_stage(125.0)
    assert stage == "Toxicity"
    assert status == "High"


def test_vitamin_d_sufficiency_stage():
    """
    Case 5: Vitamin D Sufficiency (30-100 ng/mL).
    """
    stage, msg, status = classify_vitamin_d_stage(55.0)
    assert stage == "Sufficiency"
    assert status == "Normal"


def test_family_deduplication_counts_in_health_summary():
    """
    Case 6: Health Summary counts family only once.
    """
    parsed = parse_vitamin_profile_report(SAMPLE_THYROCARE_VITAMIN_PANEL)
    summary = generate_health_summary(parsed)

    # 3 total biomarkers extracted in JSON: Vitamin D Total, Vitamin D2, Vitamin D3
    assert summary["total_biomarkers"] == 3
    # Only 1 Low biomarker (Vitamin D Total), since D3/D2 are secondary family members
    assert summary["low_biomarkers"] == 1
    assert summary["abnormal_count"] == 1
    assert len(summary["abnormal_biomarkers"]) == 1
    assert summary["abnormal_biomarkers"][0]["key"] == "vitamin_d"


def test_health_highlights_deduplication():
    """
    Case 7: Health Highlights only produces card for Vitamin D Total, not D2/D3.
    """
    parsed = parse_vitamin_profile_report(SAMPLE_THYROCARE_VITAMIN_PANEL)
    highlights = generate_health_highlights(parsed)

    cards = highlights["highlights"]
    assert len(cards) == 1
    assert cards[0]["key"] == "vitamin_d"
    assert cards[0]["name"] == "Vitamin D Total"
    assert cards[0]["clinical_stage"] == "Deficiency"
    assert cards[0]["status"] == "Low"
    assert cards[0]["value"] == 12.17


def test_clinical_stage_extraction_helper():
    """
    Case 8: Helper extracts clinical range dict.
    """
    text = """
    Deficiency : <20 ng/mL
    Insufficiency : 20-30 ng/mL
    Sufficiency : 30-100 ng/mL
    Toxicity : >100 ng/mL
    """
    ranges = extract_vitamin_d_interpretation_ranges(text)
    assert ranges is not None
    assert ranges["deficiency"] == "<20"
    assert ranges["insufficiency"] == "20-30"
    assert ranges["sufficiency"] == "30-100"
    assert ranges["toxicity"] == ">100"


def test_reference_source_report_when_interpretation_ranges_present():
    """
    Case 9: Reference source is 'report' when interpretation ranges are present.
    """
    parsed = parse_vitamin_profile_report(SAMPLE_THYROCARE_VITAMIN_PANEL)
    vit_d = next(b for b in parsed["biomarkers"] if b["key"] == "vitamin_d")
    assert vit_d["reference_source"] == "report"


def test_biomarker_ordering():
    """
    Case 10: Biomarker ordering puts Vitamin D Total first, then D3/D2, followed by other vitamins.
    """
    full_report = """
    VITAMIN D TOTAL : 12.17 ng/mL
    VITAMIN D2 : 1.15 ng/mL
    VITAMIN D3 : 11.02 ng/mL
    VITAMIN B12 : 250 pg/mL
    FOLATE : 12 ng/mL
    FERRITIN : 100 ng/mL
    SERUM IRON : 80 ug/dL
    """
    parsed = parse_vitamin_profile_report(full_report)
    keys = [b["key"] for b in parsed["biomarkers"]]

    assert keys[0] == "vitamin_d"
    assert keys[1] == "vitamin_d3"
    assert keys[2] == "vitamin_d2"
    assert keys[3] == "vitamin_b12"
