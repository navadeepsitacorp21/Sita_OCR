"""
Medical Natural-Language Explanation Engine (Zero-LLM Deterministic Layer).

Generates human-readable, educational explanations from verified deterministic
laboratory analysis outputs (biomarkers, observed values, reference ranges,
statuses, detected patterns, and longitudinal trends).

Strict Safety Principles:
- ZERO LLM or generative AI dependencies.
- 100% deterministic template-driven synthesis (no randomness).
- NEVER calculates or alters clinical facts, values, or reference ranges.
- NEVER issues clinical diagnoses, treatment recommendations, or medication advice.
- Uses safe, non-diagnostic educational language.
"""

from typing import Dict, Any, List, Optional
from app.services.medical_rule_engine import _INTERPRETATION_REGISTRY


DISCLAIMER_TEXT = (
    "This explanation is educational and does not replace advice from a qualified healthcare professional."
)


def _get_panel_meta(report_type: str) -> Dict[str, str]:
    """Resolves human-friendly names and adjectives for laboratory panels."""
    rt = (report_type or "").upper()
    if "CBC" in rt or "BLOOD" in rt:
        return {"code": "CBC", "name": "CBC", "full_name": "Complete Blood Count (CBC)", "adjective": "blood-related"}
    elif "LFT" in rt or "LIVER" in rt:
        return {"code": "LFT", "name": "LFT", "full_name": "Liver Function Test (LFT)", "adjective": "liver-related"}
    elif "KFT" in rt or "KIDNEY" in rt or "RENAL" in rt:
        return {"code": "KFT", "name": "KFT", "full_name": "Kidney Function Test (KFT)", "adjective": "kidney-related"}
    elif "LIPID" in rt:
        return {"code": "LIPID", "name": "Lipid Profile", "full_name": "Lipid Profile", "adjective": "lipid-related"}
    elif "THYROID" in rt:
        return {"code": "THYROID", "name": "Thyroid Panel", "full_name": "Thyroid Function Panel", "adjective": "thyroid-related"}
    elif "URINE" in rt:
        return {"code": "URINE", "name": "Urine Routine", "full_name": "Urine Routine Examination", "adjective": "urine"}
    elif "VITAMIN" in rt:
        return {"code": "VITAMIN", "name": "Vitamin Panel", "full_name": "Vitamin Panel", "adjective": "vitamin"}
    else:
        clean_name = report_type.replace("_", " ").title() if report_type else "Laboratory"
        return {"code": rt or "LAB", "name": clean_name, "full_name": f"{clean_name} Report", "adjective": "tested"}


def _format_reasons(associations: List[str]) -> str:
    """Formats raw rule associations into safe, conversational text without diagnoses."""
    if not associations:
        return "various physiological factors"
    # Take up to 3 associations and lowercase the first letter for natural flow
    clean = []
    for a in associations[:3]:
        s = a.strip().rstrip(".")
        if s:
            clean.append(s[0].lower() + s[1:])
    if len(clean) == 1:
        return clean[0]
    elif len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    else:
        return f"{', '.join(clean[:-1])}, or {clean[-1]}"


def generate_overall_explanation(
    report_type: str,
    total: int,
    normal: int,
    low: int,
    high: int,
    needs_review: int,
    abnormal_bms: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Produces a natural, non-robotic overall explanation of the test findings.
    """
    panel_meta = _get_panel_meta(report_type)
    panel_name = panel_meta["name"]
    panel_adj = panel_meta["adjective"]
    abnormal = low + high
    abnormal_bms = abnormal_bms or []

    if total == 0:
        return f"No {panel_name} parameters were available for evaluation."

    # Case 1: All parameters are normal and none require review
    if normal == total and needs_review == 0:
        return (
            "Overall, the reported results are reassuring, with all measured parameters "
            "falling within the laboratory's reference ranges. No significant abnormal "
            "pattern was identified from the available results."
        )

    # Case 2: Only needs_review (no abnormal values, but some parameters lacked context)
    if abnormal == 0 and needs_review > 0:
        if needs_review == 1:
            return (
                f"Most of your {panel_name} results are within standard laboratory ranges. "
                "One parameter could not be evaluated against a definitive reference range and "
                "requires clinical review, while the remaining results are within range."
            )
        else:
            return (
                f"Most of your {panel_name} results are within standard laboratory ranges. "
                f"{needs_review} parameters require clinical review because reference information "
                "in the report was incomplete or dependent on demographic context."
            )

    # Case 3: Exactly 1 abnormal parameter
    if abnormal == 1:
        bm = abnormal_bms[0]
        bm_name = bm.get("name") or bm.get("key", "").replace("_", " ").title()
        status_dir = "above" if str(bm.get("status", "")).lower() == "high" else "below"
        if needs_review == 0:
            return (
                f"Overall, most of your {panel_name} results are within the laboratory's expected reference ranges. "
                f"{bm_name} is {status_dir} its reported range, while the remaining results are within range."
            )
        else:
            return (
                f"Most of your {panel_name} results are within expected ranges. "
                f"{bm_name} is {status_dir} its reported range, and {needs_review} parameter(s) require "
                "clinical review for reference verification."
            )

    # Case 4: Exactly 2 abnormal parameters
    if abnormal == 2:
        bm1 = abnormal_bms[0]
        bm2 = abnormal_bms[1]
        name1 = bm1.get("name") or bm1.get("key", "").replace("_", " ").title()
        name2 = bm2.get("name") or bm2.get("key", "").replace("_", " ").title()
        dir1 = "above" if str(bm1.get("status", "")).lower() == "high" else "below"
        dir2 = "above" if str(bm2.get("status", "")).lower() == "high" else "below"

        if dir1 == dir2:
            return (
                f"Your {panel_name} is mostly within the laboratory's expected ranges. "
                f"Both {name1} and {name2} are {dir1} their reported ranges, while the remaining "
                f"reported {panel_adj} parameters are within range."
            )
        else:
            return (
                f"Your {panel_name} is mostly within the laboratory's expected ranges. "
                f"{name1} is {dir1} the reported range, while {name2} is {dir2} it. "
                f"The remaining reported {panel_adj} parameters are within range."
            )

    # Case 5: 3 to 4 abnormal parameters
    if 3 <= abnormal <= 4:
        return (
            f"Most of your {panel_name} results are within the expected laboratory ranges. "
            "A few values are outside their respective ranges and are worth discussing "
            "in the context of your overall health and other test results."
        )

    # Case 6: 5 or more abnormal parameters
    return (
        f"Several values in your {panel_name} are outside the expected laboratory ranges "
        "and are worth reviewing in the context of your overall health, symptoms, and clinical history."
    )


def generate_abnormal_findings_explanation(
    biomarkers: List[Dict[str, Any]]
) -> List[str]:
    """
    Generates bulleted key findings that highlight parameters outside reference ranges
    or requiring clinical review.
    """
    findings: List[str] = []
    for bm in biomarkers:
        st = str(bm.get("status", "")).lower()
        name = bm.get("name") or bm.get("key", "").replace("_", " ").title()
        val = bm.get("value")
        unit = bm.get("unit") or ""
        unit_str = f" {unit}" if unit else ""
        ref = bm.get("reference_range")

        if st == "high":
            if val is not None and ref:
                findings.append(f"{name} is elevated ({val}{unit_str} vs reference {ref}{unit_str}).")
            else:
                findings.append(f"{name} is elevated above the reported reference range.")
        elif st == "low":
            if val is not None and ref:
                findings.append(f"{name} is below the reported range ({val}{unit_str} vs reference {ref}{unit_str}).")
            else:
                findings.append(f"{name} is below the reported reference range.")
        elif st in ("needs review", "needs_review", "unknown"):
            findings.append(f"{name} requires clinical review for reference interval confirmation.")

    if not findings:
        findings.append("All measured parameters fall within standard biological reference ranges.")

    return findings


def generate_biomarker_explanation(
    bm: Dict[str, Any],
    report_type: str = "LAB",
    patient_gender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs a safe, non-diagnostic educational explanation for an abnormal
    or needs_review biomarker using existing interpretation rules.
    """
    k = bm.get("key", "").lower()
    name = bm.get("name") or k.replace("_", " ").title()
    status_raw = str(bm.get("status", "")).lower()
    val = bm.get("value")
    unit = bm.get("unit") or ""
    ref = bm.get("reference_range") or "—"
    panel_meta = _get_panel_meta(report_type)
    panel_adj = panel_meta["adjective"]

    entry = _INTERPRETATION_REGISTRY.get(k, {})
    status_clean = "high" if "high" in status_raw else ("low" if "low" in status_raw else "needs_review")

    # 1. Needs Review handling
    if status_clean == "needs_review":
        status_reason = str(bm.get("status_reason", "")).lower()
        is_gender_issue = (
            not patient_gender
            or patient_gender.strip().lower() in ("unknown", "not_specified", "")
            or "gender" in status_reason
        )
        if is_gender_issue:
            exp = (
                f"{name} could not be confidently evaluated because gender-specific reference "
                "information was not provided to establish the appropriate reference range."
            )
        else:
            exp = (
                f"{name} could not be confidently interpreted because the required reference "
                "information is incomplete or unclear in the report."
            )
        return {
            "biomarker": name,
            "status": "needs_review",
            "explanation": exp
        }

    # 2. High / Low handling
    interp = entry.get(status_clean, {})
    assocs = interp.get("possible_associations", [])
    reasons_text = _format_reasons(assocs)

    if status_clean == "high":
        direction_phrase = "above the laboratory's reported range"
        variation_phrase = f"Elevated levels can occur with factors such as {reasons_text}."
    else:
        direction_phrase = "below the laboratory's reported range"
        variation_phrase = f"Lower values can be associated with {reasons_text}."

    if assocs:
        explanation = (
            f"{name} is {direction_phrase}. {variation_phrase} This result is best "
            f"interpreted together with your other {panel_adj} results and overall clinical context."
        )
    else:
        what_it_measures = entry.get("what_it_measures")
        if what_it_measures:
            explanation = (
                f"{name} is {direction_phrase}. Because {what_it_measures.lower()}, "
                f"this result is best considered in context with your other {panel_adj} findings."
            )
        else:
            explanation = (
                f"{name} is {direction_phrase} ({val} {unit} vs reference {ref}). "
                f"This finding should be discussed with your healthcare provider in the context of your overall health."
            )

    return {
        "biomarker": name,
        "status": status_clean,
        "explanation": explanation
    }


def generate_pattern_explanation(
    patterns: List[Dict[str, Any]],
    report_interpretation: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Transforms cross-biomarker patterns into clear educational descriptions.
    """
    explanations: List[Dict[str, Any]] = []
    for pat in patterns:
        name = pat.get("name", "Physiological Pattern")
        note = pat.get("educational_note", "")
        summary = pat.get("summary", "")
        rec = pat.get("recommendation", "")

        parts = []
        if summary:
            parts.append(summary)
        if note:
            parts.append(note)
        if rec and not rec.endswith("."):
            rec += "."
        if rec:
            parts.append(f"Clinical consideration: {rec}")

        if pat.get("pattern_id") == "anemia_pattern" and report_interpretation and report_interpretation.get("text"):
            parts.append(
                f"Laboratory report note: \"{report_interpretation['text']}\". This source observation should be clinically confirmed with your doctor."
            )

        explanations.append({
            "pattern": name,
            "explanation": " ".join(parts)
        })

    return explanations


def generate_trend_explanation(
    trends: Optional[Dict[str, Any]]
) -> str:
    """
    Produces a natural-language description of longitudinal changes using only verified trend data.
    """
    if not trends or not isinstance(trends, dict):
        return "There is not enough previous report data to identify a meaningful trend."

    # Check for multi-report consistent trends first
    multi_trends = [
        t.get("multi_report_trend")
        for t in trends.values()
        if t.get("multi_report_trend")
    ]
    if multi_trends:
        return " ".join(multi_trends)

    # Collect single-step direction changes
    increased = []
    decreased = []
    steady = []

    for k, t in trends.items():
        name = t.get("name") or k.replace("_", " ").title()
        dir_str = t.get("direction", "")
        cur = t.get("current_value")
        prev = t.get("previous_value")
        unit = t.get("unit") or ""
        unit_str = f" {unit}" if unit else ""

        if dir_str == "increased":
            increased.append(f"{name} (from {prev} to {cur}{unit_str})")
        elif dir_str == "decreased":
            decreased.append(f"{name} (from {prev} to {cur}{unit_str})")
        elif dir_str == "stable":
            steady.append(name)

    narrative_parts = []
    if increased:
        if len(increased) == 1:
            narrative_parts.append(f"Compared with your previous report, {increased[0]} has increased.")
        else:
            narrative_parts.append(f"Compared with your previous report, increases were noted in {', '.join(increased)}.")

    if decreased:
        if len(decreased) == 1:
            narrative_parts.append(f"Compared with your previous report, {decreased[0]} has decreased.")
        else:
            narrative_parts.append(f"Compared with your previous report, decreases were noted in {', '.join(decreased)}.")

    if not increased and not decreased and steady:
        narrative_parts.append("Tracked laboratory parameters have remained steady compared with your previous report.")

    if not narrative_parts:
        return "There is not enough previous report data to identify a meaningful trend."

    return " ".join(narrative_parts)


def generate_doctor_discussion_points(
    biomarkers: List[Dict[str, Any]],
    patterns: Optional[List[Dict[str, Any]]] = None,
    trends: Optional[Dict[str, Any]] = None,
    needs_review_count: int = 0,
    report_interpretation: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Builds structured, conversational talking points for consulting a doctor.
    """
    points: List[str] = []
    patterns = patterns or []
    trends = trends or {}

    abnormals = [
        bm for bm in biomarkers
        if str(bm.get("status", "")).lower() in ("high", "low")
    ]

    # Specific points for abnormal biomarkers based on registry rules
    for bm in abnormals:
        k = bm.get("key", "").lower()
        name = bm.get("name") or k.replace("_", " ").title()
        st = str(bm.get("status", "")).lower()
        entry = _INTERPRETATION_REGISTRY.get(k, {})
        interp = entry.get(st, {})
        rec = interp.get("recommendation", "")

        if "creatinine" in k:
            points.append(
                f"Discuss the {name} elevation in relation to hydration, physical activity, and kidney function."
            )
        elif "urea" in k or "bun" in k:
            points.append(
                f"Review {name} levels in conjunction with dietary protein, fluid intake, and renal markers."
            )
        elif "phosphorus" in k:
            points.append(
                f"Review {name} levels to determine whether dietary factors, calcium balance, or medication effects are contributing."
            )
        elif "calcium" in k:
            points.append(
                f"Discuss {name} levels in connection with vitamin D status, bone health, and albumin levels."
            )
        elif "alt" in k or "ast" in k or "transaminase" in k:
            points.append(
                f"Review liver transaminase levels ({name}) in relation to current medications, supplements, or lifestyle factors."
            )
        elif "alkaline_phosphatase" in k or "ggt" in k or "bilirubin" in k:
            points.append(
                f"Review biliary markers ({name}) to see if liver or gallbladder evaluation is indicated."
            )
        elif "mcv" in k or "mch" in k or "hemoglobin" in k:
            points.append(
                f"Discuss red blood cell indices ({name}) to determine whether iron studies or nutritional evaluation are warranted."
            )
        elif "wbc" in k or "neutrophil" in k:
            points.append(
                f"Review white blood cell counts ({name}) in the context of recent infections, inflammation, or physical stress."
            )
        elif "platelet" in k:
            points.append(
                f"Discuss platelet count ({name}) and check for any symptoms such as unusual bruising or bleeding."
            )
        elif "cholesterol" in k or "ldl" in k or "lipid" in k:
            points.append(
                f"Discuss lipid levels ({name}) in the context of nutrition, physical activity, and family history."
            )
        elif "triglyceride" in k:
            points.append(
                f"Review {name} in connection with dietary habits, fasting status, and metabolic health."
            )
        elif "hdl" in k:
            points.append(
                f"Discuss {name} levels and lifestyle measures that support healthy lipoprotein balance."
            )
        elif rec and "consult" not in rec.lower():
            points.append(f"Discuss {name} findings: {rec.rstrip('.')}.")
        else:
            points.append(f"Review {name} ({bm.get('value')} {bm.get('unit') or ''}) in the context of your overall clinical history.")

    # Deduplicate while preserving order
    seen = set()
    deduped_points = []
    for p in points:
        if p not in seen:
            seen.add(p)
            deduped_points.append(p)
    points = deduped_points[:4]

    # Pattern discussion point
    for pat in patterns[:2]:
        p_name = pat.get("name", "Observed Pattern")
        points.append(
            f"Ask your doctor about the observed '{p_name}' and whether further evaluation or repeat testing is advised."
        )

    # Source laboratory note discussion point
    if report_interpretation and report_interpretation.get("text"):
        points.append(
            f"Discuss the laboratory report note ('{report_interpretation['text']}') with your doctor for clinical correlation."
        )

    # Needs Review point
    if needs_review_count > 0:
        points.append(
            "Clarify reference ranges for parameters marked 'Needs Review' using your printed laboratory report."
        )

    # All Normal fallback
    if not points:
        points.append("Review these reassuring results at your next routine healthcare consultation.")
        points.append("Discuss appropriate timing and lifestyle habits to maintain healthy laboratory markers.")

    return points


def generate_medical_explanation(
    analysis_output: Optional[Dict[str, Any]] = None,
    report_type: Optional[str] = None,
    biomarkers: Optional[List[Dict[str, Any]]] = None,
    patterns: Optional[List[Dict[str, Any]]] = None,
    trends: Optional[Dict[str, Any]] = None,
    summary: Optional[Dict[str, Any]] = None,
    patient_gender: Optional[str] = None,
    report_date: Optional[str] = None,
    report_interpretation: Optional[Dict[str, Any]] = None,
    consistency_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for generating the complete natural-language explanation.
    Can be called either with a full analysis dictionary or with discrete arguments.
    """
    if analysis_output and isinstance(analysis_output, dict):
        report_type = report_type or analysis_output.get("report_type") or "LAB"
        biomarkers = biomarkers if biomarkers is not None else analysis_output.get("biomarkers", [])
        patterns = patterns if patterns is not None else analysis_output.get("patterns", [])
        trends = trends if trends is not None else analysis_output.get("trends", {})
        summary = summary if summary is not None else analysis_output.get("summary", {})
        patient_gender = patient_gender or analysis_output.get("patient_gender")
        report_date = report_date or analysis_output.get("report_date")
        report_interpretation = report_interpretation or analysis_output.get("report_interpretation")
    else:
        report_type = report_type or "LAB"
        biomarkers = biomarkers or []
        patterns = patterns or []
        trends = trends or {}
        summary = summary or {}

    total = len(biomarkers)
    normal = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() == "normal")
    low = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() == "low")
    high = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() == "high")
    needs_review = sum(
        1 for bm in biomarkers
        if str(bm.get("status", "")).lower() in ("needs review", "needs_review", "unknown")
    )

    abnormal_bms = [
        bm for bm in biomarkers
        if str(bm.get("status", "")).lower() in ("low", "high", "needs review", "needs_review", "unknown")
    ]

    # 1. Overall explanation
    overall = generate_overall_explanation(
        report_type=report_type,
        total=total,
        normal=normal,
        low=low,
        high=high,
        needs_review=needs_review,
        abnormal_bms=abnormal_bms
    )

    # 2. Key findings
    key_findings = generate_abnormal_findings_explanation(biomarkers)

    # 3. Individual biomarker explanations for abnormal or needs_review items
    bm_explanations = [
        generate_biomarker_explanation(bm, report_type=report_type, patient_gender=patient_gender)
        for bm in abnormal_bms
    ]

    # 4. Pattern explanations
    pattern_explanations = generate_pattern_explanation(patterns, report_interpretation=report_interpretation)

    # 5. Trend explanation
    trend_explanation = generate_trend_explanation(trends)

    # 6. Doctor discussion points
    doctor_discussion = generate_doctor_discussion_points(
        biomarkers=biomarkers,
        patterns=patterns,
        trends=trends,
        needs_review_count=needs_review,
        report_interpretation=report_interpretation
    )

    consistency_warning = None
    if consistency_result and not consistency_result.get("is_consistent", True):
        consistency_warning = (
            "Some reported lipid values appear internally inconsistent. The displayed values are preserved "
            "from the laboratory report and should be verified against the original report."
        )

    return {
        "overall_explanation": overall,
        "key_findings": key_findings,
        "biomarker_explanations": bm_explanations,
        "pattern_explanations": pattern_explanations,
        "trend_explanation": trend_explanation,
        "doctor_discussion": doctor_discussion,
        "consistency_warning": consistency_warning,
        "disclaimer": DISCLAIMER_TEXT
    }
