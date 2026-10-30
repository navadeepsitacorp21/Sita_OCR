import logging
import math
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_lipid_consistency(biomarkers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Consistency validation layer executed AFTER extraction but BEFORE the deterministic rule engine.
    This validation does NOT modify or overwrite extracted values.

    Checks evaluated relationships:
    1. Non-HDL Cholesterol ≈ Total Cholesterol - HDL
    2. Total Cholesterol / HDL Ratio ≈ Total Cholesterol / HDL
    3. LDL / HDL Ratio ≈ LDL / HDL
    4. Friedewald Formula (if Triglycerides < 400): LDL ≈ Total Cholesterol - HDL - (Triglycerides / 5)

    Accounts for decimal precision, standard lab rounding (±1.5 mg/dL or ±0.2 ratio units),
    and differing formula conventions.

    Returns:
    {
        "is_consistent": bool,
        "warnings": List[str],
        "checks": List[Dict[str, Any]]
    }
    """
    val_map: Dict[str, float] = {}
    for bm in biomarkers:
        key = bm.get("key", "").lower()
        val = bm.get("value")
        if val is not None and isinstance(val, (int, float)):
            val_map[key] = float(val)

    warnings: List[str] = []
    checks: List[Dict[str, Any]] = []

    tc = val_map.get("total_cholesterol")
    hdl = val_map.get("hdl")
    ldl = val_map.get("ldl")
    tg = val_map.get("triglycerides")
    non_hdl = val_map.get("non_hdl")
    tc_hdl_ratio = val_map.get("cholesterol_hdl_ratio")
    ldl_hdl_ratio = val_map.get("ldl_hdl_ratio")

    # Check 1: Non-HDL ≈ TC - HDL
    if tc is not None and hdl is not None and non_hdl is not None:
        expected_non_hdl = tc - hdl
        diff = abs(non_hdl - expected_non_hdl)
        # Tolerance: ±2.0 mg/dL for rounding
        is_ok = diff <= 2.5
        checks.append({
            "relationship": "non_hdl_calculation",
            "formula": "Non-HDL ≈ Total Cholesterol - HDL",
            "reported_value": non_hdl,
            "expected_value": round(expected_non_hdl, 1),
            "difference": round(diff, 2),
            "status": "consistent" if is_ok else "inconsistent"
        })
        if not is_ok:
            warn = (
                f"Reported Non-HDL ({non_hdl} mg/dL) differs from mathematically expected "
                f"Total Cholesterol ({tc}) - HDL ({hdl}) = {round(expected_non_hdl, 1)} mg/dL."
            )
            warnings.append(warn)
            logger.warning("[LipidConsistency] %s", warn)

    # Check 2: TC/HDL Ratio ≈ TC / HDL
    if tc is not None and hdl is not None and hdl > 0 and tc_hdl_ratio is not None:
        expected_ratio = tc / hdl
        diff = abs(tc_hdl_ratio - expected_ratio)
        # Tolerance: ±0.2 for ratio rounding (e.g. 6.5 vs 6.526)
        is_ok = diff <= 0.25
        checks.append({
            "relationship": "tc_hdl_ratio_calculation",
            "formula": "TC/HDL Ratio ≈ Total Cholesterol / HDL",
            "reported_value": tc_hdl_ratio,
            "expected_value": round(expected_ratio, 2),
            "difference": round(diff, 2),
            "status": "consistent" if is_ok else "inconsistent"
        })
        if not is_ok:
            warn = (
                f"Reported TC/HDL Ratio ({tc_hdl_ratio}) differs from mathematically expected "
                f"Total Cholesterol ({tc}) / HDL ({hdl}) = {round(expected_ratio, 2)}."
            )
            warnings.append(warn)
            logger.warning("[LipidConsistency] %s", warn)

    # Check 3: LDL/HDL Ratio ≈ LDL / HDL
    if ldl is not None and hdl is not None and hdl > 0 and ldl_hdl_ratio is not None:
        expected_ratio = ldl / hdl
        diff = abs(ldl_hdl_ratio - expected_ratio)
        # Tolerance: ±0.2 for ratio rounding (e.g. 4.5 vs 4.526)
        is_ok = diff <= 0.25
        checks.append({
            "relationship": "ldl_hdl_ratio_calculation",
            "formula": "LDL/HDL Ratio ≈ LDL / HDL",
            "reported_value": ldl_hdl_ratio,
            "expected_value": round(expected_ratio, 2),
            "difference": round(diff, 2),
            "status": "consistent" if is_ok else "inconsistent"
        })
        if not is_ok:
            warn = (
                f"Reported LDL/HDL Ratio ({ldl_hdl_ratio}) differs from mathematically expected "
                f"LDL ({ldl}) / HDL ({hdl}) = {round(expected_ratio, 2)}."
            )
            warnings.append(warn)
            logger.warning("[LipidConsistency] %s", warn)

    # Check 4: Friedewald formula (informational cross-check if TG < 400)
    if tc is not None and hdl is not None and ldl is not None and tg is not None and tg < 400:
        expected_ldl = tc - hdl - (tg / 5.0)
        diff = abs(ldl - expected_ldl)
        # Tolerance: ±5.0 mg/dL for direct vs calculated LDL assays
        checks.append({
            "relationship": "friedewald_ldl_reference",
            "formula": "Friedewald LDL ≈ TC - HDL - (TG / 5)",
            "reported_value": ldl,
            "expected_value": round(expected_ldl, 1),
            "difference": round(diff, 2),
            "status": "consistent" if diff <= 5.0 else "discrepant_assay_or_formula"
        })

    is_consistent = len(warnings) == 0

    return {
        "is_consistent": is_consistent,
        "warnings": warnings,
        "checks": checks
    }

