from typing import Optional, Tuple, Dict, Any

VALIDATION_RANGES: Dict[str, Tuple[float, float]] = {
    # CBC
    "wbc_count_cumm": (1000.0, 50000.0),
    "wbc_count_thou": (1.0, 50.0),
    "platelet_count_cumm": (20000.0, 1000000.0),
    "platelet_count_thou": (20.0, 1000.0),
    "mcv": (50.0, 130.0),
    "mchc": (20.0, 40.0),
    "mch": (10.0, 50.0),
    "mpv": (3.0, 20.0),
    "rdw_cv": (5.0, 35.0),
    "rdw_sd": (20.0, 80.0),
    "rdw": (5.0, 35.0),
    "hemoglobin": (3.0, 25.0),
    "pcv": (15.0, 75.0),
    "rbc_count": (1.0, 10.0),
    "neutrophils": (0.0, 100.0),
    "lymphocytes": (0.0, 100.0),
    "monocytes": (0.0, 100.0),
    "eosinophils": (0.0, 100.0),
    "basophils": (0.0, 100.0),

    # LFT
    "total_bilirubin": (0.0, 25.0),
    "direct_bilirubin": (0.0, 10.0),
    "indirect_bilirubin": (0.0, 20.0),
    "alt_sgpt": (0.0, 1000.0),
    "ast_sgot": (0.0, 1000.0),
    "alkaline_phosphatase": (20.0, 1500.0),
    "ggt": (5.0, 500.0),
    "total_protein": (2.0, 12.0),
    "albumin": (1.0, 8.0),
    "globulin": (0.5, 8.0),
    "albumin_globulin_ratio": (0.5, 3.5),
    "ldh": (50.0, 1500.0),

    # KFT
    "serum_urea": (1.0, 300.0),
    "bun": (1.0, 150.0),
    "serum_creatinine": (0.1, 30.0),
    "egfr": (5.0, 250.0),
    "uric_acid": (0.5, 25.0),
    "sodium": (50.0, 200.0),
    "potassium": (1.0, 10.0),
    "chloride": (50.0, 180.0),
    "bicarbonate": (5.0, 60.0),
    "calcium": (2.0, 20.0),
    "phosphorus": (0.5, 15.0),
    "magnesium": (0.5, 10.0),
    "urea_creatinine_ratio": (1.0, 100.0),

    # Lipid Profile
    "total_cholesterol": (50.0, 1000.0),
    "triglycerides": (10.0, 2500.0),
    "hdl": (5.0, 200.0),
    "ldl": (10.0, 600.0),
    "vldl": (1.0, 300.0),
    "non_hdl": (20.0, 900.0),
    "cholesterol_hdl_ratio": (0.5, 30.0),
    "ldl_hdl_ratio": (0.1, 20.0),
    "apolipoprotein_a1": (10.0, 400.0),
    "apolipoprotein_b": (10.0, 350.0),
    "apob_apoa1_ratio": (0.05, 10.0)
}


def validate_biomarker_value_bounds(key: str, value: Optional[float], unit: str = "") -> Tuple[bool, str]:
    """
    Step 6: Validator Upgrade
    Validates values against physiological bounds.
    Returns (is_valid, reason).
    """
    if value is None:
        return False, "Value is missing or None."

    if value < 0:
        return False, "Physiological validation failed: Negative value."

    unit_lower = (unit or "").lower()

    if key in ["wbc_count", "tlc"]:
        if value >= 100:
            min_val, max_val = VALIDATION_RANGES["wbc_count_cumm"]
        else:
            min_val, max_val = VALIDATION_RANGES["wbc_count_thou"]
        if value < min_val or value > max_val:
            return False, "Physiological validation failed."

    elif key in ["platelet_count", "plt"]:
        if value >= 1000:
            min_val, max_val = VALIDATION_RANGES["platelet_count_cumm"]
        elif "lakh" in unit_lower or "lac" in unit_lower or value < 20.0:
            min_val, max_val = (0.20, 10.0)
        else:
            min_val, max_val = VALIDATION_RANGES["platelet_count_thou"]
        if value < min_val or value > max_val:
            return False, "Physiological validation failed."

    elif key in VALIDATION_RANGES:
        min_val, max_val = VALIDATION_RANGES[key]
        if value < min_val or value > max_val:
            return False, "Physiological validation failed."

    return True, "passed"


def validate_cbc_biomarker(key: str, value: Optional[float], unit: str = "") -> Tuple[bool, str]:
    return validate_biomarker_value_bounds(key, value, unit)


def validate_biomarker_dict(biomarker_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a biomarker dictionary and attach validation status/reason.
    If validation fails:
    status becomes "Needs Review", reason becomes "Physiological validation failed."
    """
    key = biomarker_dict.get("key", "")
    value = biomarker_dict.get("value")
    unit = biomarker_dict.get("unit", "")

    is_valid, reason = validate_biomarker_value_bounds(key, value, unit)

    res = dict(biomarker_dict)
    if not is_valid:
        res["status"] = "Needs Review"
        res["status_reason"] = reason
        res["validation_status"] = "failed"
        res["validation_reason"] = reason
    else:
        res["validation_status"] = "passed"
        res["validation_reason"] = "passed"

    return res
