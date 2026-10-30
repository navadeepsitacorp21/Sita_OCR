import pytest
from app.utils.alias_resolver import resolve_biomarker_alias, normalize_text_for_alias_matching


def test_alias_normalization_cleanups():
    assert normalize_text_for_alias_matching("H B 14.5") == "hb 14.5"
    assert normalize_text_for_alias_matching("H.G.B: 12.0") == "hgb 12.0"
    assert normalize_text_for_alias_matching("W.B.C (Total Count)") == "wbc total count"
    assert normalize_text_for_alias_matching("Plate lets 250000") == "platelets 250000"
    assert normalize_text_for_alias_matching("Bilirubln Total 1.2") == "bilirubin total 1.2"
    assert normalize_text_for_alias_matching("Haemoglobin 13.5") == "haemoglobin 13.5"
    assert normalize_text_for_alias_matching("Neut% 65") == "neut % 65"


def test_cbc_aliases_resolution():
    # 1. Hb -> Hemoglobin
    res = resolve_biomarker_alias("Hb 13.5 g/dL")
    assert res is not None
    assert res["canonical_key"] == "hemoglobin"

    # 2. HGB -> Hemoglobin
    res = resolve_biomarker_alias("HGB: 14.2 gm/dL")
    assert res is not None
    assert res["canonical_key"] == "hemoglobin"

    # 3. Haemoglobin -> Hemoglobin
    res = resolve_biomarker_alias("Haemoglobin 12.1 g/dL")
    assert res is not None
    assert res["canonical_key"] == "hemoglobin"

    # 4. TLC -> WBC Count
    res = resolve_biomarker_alias("TLC 6500 /cumm")
    assert res is not None
    assert res["canonical_key"] == "wbc_count"

    # 5. Total Count -> WBC Count
    res = resolve_biomarker_alias("Total Count 7200 /cu.mm")
    assert res is not None
    assert res["canonical_key"] == "wbc_count"

    # 6. HCT -> PCV
    res = resolve_biomarker_alias("HCT 41 %")
    assert res is not None
    assert res["canonical_key"] == "pcv"

    # 7. Hematocrit -> PCV
    res = resolve_biomarker_alias("Hematocrit 40.5 %")
    assert res is not None
    assert res["canonical_key"] == "pcv"

    # 8. Platelets -> Platelet Count
    res = resolve_biomarker_alias("Platelets 320000 /cumm")
    assert res is not None
    assert res["canonical_key"] == "platelet_count"

    # 9. PLT -> Platelet Count
    res = resolve_biomarker_alias("PLT 280 10^3/uL")
    assert res is not None
    assert res["canonical_key"] == "platelet_count"

    # 10. PMN -> Neutrophils
    res = resolve_biomarker_alias("PMN 62 %")
    assert res is not None
    assert res["canonical_key"] == "neutrophils"

    # 11. RDW-CV -> rdw_cv
    res = resolve_biomarker_alias("RDW-CV 13.5 %")
    assert res is not None
    assert res["canonical_key"] in ["rdw_cv", "rdw"]


def test_alias_priority_longest_match_first():
    # 12. Free T4 priority over T4 Total
    res = resolve_biomarker_alias("Free T4 1.2 ng/dL")
    assert res is not None
    assert res["canonical_key"] == "free_t4"
    assert res["matched_alias"] == "free t4"

    # 13. Total Bilirubin priority over Bilirubin
    res = resolve_biomarker_alias("Total Bilirubin 0.8 mg/dL")
    assert res is not None
    assert res["canonical_key"] == "total_bilirubin"
    assert res["matched_alias"] == "total bilirubin"

    # 14. Vitamin B12 priority over B12
    res = resolve_biomarker_alias("Serum Vitamin B12 450 pg/mL")
    assert res is not None
    assert res["canonical_key"] == "vitamin_b12"

    # 15. Blood Urea Nitrogen priority over Blood Urea
    res = resolve_biomarker_alias("Blood Urea Nitrogen 14 mg/dL")
    assert res is not None
    assert res["canonical_key"] == "blood_urea_nitrogen"
    assert res["matched_alias"] == "blood urea nitrogen"


def test_alias_resolver_allowed_keys_scoping():
    # When scoped to CBC, Free T4 should not resolve
    res = resolve_biomarker_alias("Free T4 1.2 ng/dL", allowed_keys=["hemoglobin", "wbc_count"])
    assert res is None

    # When scoped to CBC, HGB resolves
    res = resolve_biomarker_alias("HGB 14.0", allowed_keys=["hemoglobin", "wbc_count"])
    assert res is not None
    assert res["canonical_key"] == "hemoglobin"
