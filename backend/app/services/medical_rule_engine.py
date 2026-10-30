import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("sita.medical_engine")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES_PATH = os.path.join(BASE_DIR, "data", "medical_interpretation_rules.json")


def load_interpretation_registry() -> Dict[str, Any]:
    """Load the deterministic biomarker interpretation database."""
    if os.path.exists(RULES_PATH):
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load medical interpretation rules: {e}")
    return {}


_INTERPRETATION_REGISTRY: Dict[str, Any] = load_interpretation_registry()


def interpret_biomarker(
    key: str,
    status: str,
    value: Optional[float] = None,
    unit: str = "",
    reference_range: str = ""
) -> Dict[str, Any]:
    """
    Returns deterministic educational explanation for an individual biomarker.
    """
    entry = _INTERPRETATION_REGISTRY.get(key.lower(), {})
    status_lower = (status or "unknown").lower()

    what_it_measures = entry.get("what_it_measures", f"Measures circulating {key.replace('_', ' ')}.")
    interp_data = entry.get(status_lower, {})

    if not interp_data:
        if status_lower in ("needs review", "unknown"):
            return {
                "what_it_measures": what_it_measures,
                "title": f"{entry.get('name', key.title())}: Needs Clinical Review",
                "description": "This parameter could not be automatically evaluated against a definitive reference range and requires clinical review.",
                "possible_associations": [
                    "Atypical or gender-specific reference format",
                    "Demographic information required"
                ],
                "recommendation": "Review this parameter directly with your healthcare provider alongside your printed laboratory report.",
                "disclaimer": "This information is educational and does not establish a medical diagnosis."
            }
        else:
            return {
                "what_it_measures": what_it_measures,
                "title": f"{entry.get('name', key.title())}: {status}",
                "description": f"The measured value ({value} {unit}) is marked as {status}.",
                "possible_associations": [],
                "recommendation": "Consult a healthcare professional for clinical correlation.",
                "disclaimer": "This information is educational and does not establish a medical diagnosis."
            }

    return {
        "what_it_measures": what_it_measures,
        "title": interp_data.get("title", f"{key.title()} is {status}"),
        "description": interp_data.get("description", ""),
        "possible_associations": interp_data.get("possible_associations", []),
        "recommendation": interp_data.get("recommendation", "Consult your physician for personalized evaluation."),
        "disclaimer": "This information is educational and does not establish a medical diagnosis."
    }


def detect_cross_biomarker_patterns(
    biomarkers: List[Dict[str, Any]],
    report_type: str = "CBC"
) -> List[Dict[str, Any]]:
    """
    Evaluates conservative, deterministic multi-biomarker patterns.
    Never creates clinical diagnoses; produces educational pattern summaries.
    """
    patterns: List[Dict[str, Any]] = []
    status_by_key = {
        bm.get("key", "").lower(): (str(bm.get("status", "")).lower(), bm.get("value"))
        for bm in biomarkers
    }

    # Helper to check status
    def get_st(k: str) -> str:
        return status_by_key.get(k, ("unknown", None))[0]

    def get_val(k: str) -> Optional[float]:
        return status_by_key.get(k, ("unknown", None))[1]

    # --- CBC Patterns ---
    # Pattern 1: Microcytic / Hypochromic Red Cell Indices
    if get_st("mcv") == "low" and get_st("mch") == "low":
        patterns.append({
            "pattern_id": "low_red_cell_indices",
            "name": "Microcytic Hypochromic Indices",
            "severity": "attention",
            "biomarkers_involved": ["mcv", "mch"],
            "summary": "Both MCV and MCH are below the provided reference ranges.",
            "educational_note": "When both MCV and MCH are low, red blood cells are smaller and contain less hemoglobin. This pattern is commonly associated with iron deficiency, hemoglobinopathies (such as thalassemia trait), or chronic inflammation.",
            "recommendation": "Discuss with your physician to correlate with total hemoglobin and iron studies (ferritin, transferrin saturation)."
        })

    # Pattern 2: Anemia Pattern
    if get_st("hemoglobin") == "low" or get_st("rbc_count") == "low":
        involved = []
        if get_st("hemoglobin") == "low":
            involved.append("hemoglobin")
        if get_st("rbc_count") == "low":
            involved.append("rbc_count")
        if get_st("pcv") == "low":
            involved.append("pcv")

        summary_text = (
            "A low hemoglobin result was observed."
            if "hemoglobin" in involved and len(involved) == 1
            else f"{', '.join(k.replace('_', ' ').title() for k in involved)} is below reference limits."
        )

        patterns.append({
            "pattern_id": "anemia_pattern",
            "name": "Reduced Red Blood Cell Parameters",
            "severity": "attention",
            "biomarkers_involved": involved,
            "summary": summary_text,
            "educational_note": "Reduced circulating hemoglobin or hematocrit lowers blood oxygen transport. Anemias can arise from nutritional insufficiencies (iron, folate, B12), acute or chronic blood loss, or secondary to underlying medical conditions.",
            "recommendation": "Schedule a review with your clinician to identify the root cause through targeted blood testing."
        })

    # Pattern 3: Acute Inflammatory / Infection Response (Leukocytosis with Neutrophilia)
    if get_st("wbc_count") == "high" and get_st("neutrophils") == "high":
        patterns.append({
            "pattern_id": "leukocytosis_neutrophilia",
            "name": "Elevated Leukocytes with Neutrophilia",
            "severity": "attention",
            "biomarkers_involved": ["wbc_count", "neutrophils"],
            "summary": "Both total WBC count and neutrophil percentage are elevated.",
            "educational_note": "Neutrophils are the body's first responders. An elevation in both total white blood cells and neutrophils is frequently seen in acute bacterial infections, systemic inflammation, physical stress, or tissue trauma.",
            "recommendation": "Correlate with symptoms such as fever, cough, localized pain, or recent infections with your doctor."
        })

    # Pattern 4: Thrombocytopenia
    if get_st("platelet_count") == "low":
        patterns.append({
            "pattern_id": "thrombocytopenia",
            "name": "Low Platelet Count",
            "severity": "warning",
            "biomarkers_involved": ["platelet_count"],
            "summary": "Platelet count is below the provided reference range.",
            "educational_note": "Platelets are essential for blood clotting. Low counts can stem from viral infections, medications, immune consumption, or laboratory clumping (pseudo-thrombocytopenia).",
            "recommendation": "Consult a healthcare professional, especially if you notice easy bruising, petechiae, or prolonged bleeding."
        })

    # --- LFT Patterns ---
    # Pattern 5: Hepatocellular Transaminase Elevation
    if get_st("alt_sgpt") == "high" and get_st("ast_sgot") == "high":
        patterns.append({
            "pattern_id": "hepatocellular_transaminitis",
            "name": "Elevated Liver Transaminases (ALT & AST)",
            "severity": "attention",
            "biomarkers_involved": ["alt_sgpt", "ast_sgot"],
            "summary": "Both ALT and AST enzymes are elevated above the reference threshold.",
            "educational_note": "ALT and AST are intracellular enzymes released during liver cellular stress or inflammation. Common causes include fatty liver changes (steatosis), medications or supplements, alcohol exposure, or viral hepatitis.",
            "recommendation": "Review current medications, dietary supplements, and lifestyle factors with a healthcare provider."
        })

    # Pattern 6: Cholestatic / Biliary Pattern
    if get_st("alkaline_phosphatase") == "high" and (get_st("ggt") == "high" or get_st("direct_bilirubin") == "high"):
        involved = ["alkaline_phosphatase"]
        if get_st("ggt") == "high":
            involved.append("ggt")
        if get_st("direct_bilirubin") == "high":
            involved.append("direct_bilirubin")

        patterns.append({
            "pattern_id": "cholestatic_pattern",
            "name": "Biliary / Cholestatic Pattern",
            "severity": "attention",
            "biomarkers_involved": involved,
            "summary": f"{', '.join(k.replace('_', ' ').title() for k in involved)} are concurrently elevated.",
            "educational_note": "Concurrent elevation of alkaline phosphatase and biliary markers (GGT, direct bilirubin) indicates that the elevation is likely of hepatic/biliary origin rather than bone turnover.",
            "recommendation": "Consult your physician to review biliary tract health and consider liver ultrasound if clinically indicated."
        })

    # Pattern 7: Impaired Hepatic Synthetic Function (Low Albumin with Low Total Protein)
    if get_st("albumin") == "low" and get_st("total_protein") == "low":
        patterns.append({
            "pattern_id": "hypoalbuminemia_protein_loss",
            "name": "Reduced Serum Protein & Albumin",
            "severity": "attention",
            "biomarkers_involved": ["albumin", "total_protein"],
            "summary": "Both serum albumin and total protein are below normal limits.",
            "educational_note": "Albumin is synthesized exclusively by the liver. Low levels can occur in chronic liver disease, renal protein leakage (proteinuria), severe malnutrition, or systemic inflammatory states.",
            "recommendation": "Discuss with your physician to evaluate hepatic synthesis and renal protein retention."
        })

    # --- KFT Patterns ---
    # Pattern 8: Renal Impairment Pattern (Elevated Creatinine and Urea/BUN)
    if get_st("serum_creatinine") == "high" and (get_st("serum_urea") == "high" or get_st("bun") == "high"):
        involved = ["serum_creatinine"]
        if get_st("serum_urea") == "high":
            involved.append("serum_urea")
        if get_st("bun") == "high":
            involved.append("bun")

        patterns.append({
            "pattern_id": "azotemia_renal_pattern",
            "name": "Elevated Nitrogenous Waste Markers",
            "severity": "warning",
            "biomarkers_involved": involved,
            "summary": "Both creatinine and urea/BUN are elevated.",
            "educational_note": "Creatinine and urea are primary waste products filtered by the kidneys. Concurrent elevation indicates decreased renal clearance, dehydration, or altered renal blood flow.",
            "recommendation": "Consult a healthcare professional promptly to review hydration, blood pressure, and medication safety."
        })

    # Pattern 9: Electrolyte Imbalance
    elec_abnormal = [k for k in ["sodium", "potassium", "chloride", "bicarbonate"] if get_st(k) in ("high", "low")]
    if len(elec_abnormal) >= 2:
        patterns.append({
            "pattern_id": "electrolyte_imbalance",
            "name": "Electrolyte Imbalance",
            "severity": "attention",
            "biomarkers_involved": elec_abnormal,
            "summary": f"Multiple electrolytes ({', '.join(k.title() for k in elec_abnormal)}) deviate from reference ranges.",
            "educational_note": "Electrolytes maintain fluid balance, cardiac rhythm, and neuromuscular signaling. Deviations often relate to dehydration, diuretic medications, vomiting, or renal regulation.",
            "recommendation": "Review fluid intake and current medications with your doctor."
        })

    # --- Lipid Profile Patterns ---
    # Pattern 10: Elevated Circulating Lipid Levels
    high_lipids = [k for k in ["total_cholesterol", "ldl", "non_hdl", "apolipoprotein_b"] if get_st(k) == "high"]
    if len(high_lipids) >= 1:
        patterns.append({
            "pattern_id": "elevated_atherogenic_lipids",
            "name": "Elevated Circulating Lipid Levels",
            "severity": "attention",
            "biomarkers_involved": high_lipids,
            "summary": f"Elevated levels noted for {', '.join(k.replace('_', ' ').title() for k in high_lipids)}.",
            "educational_note": "Atherogenic lipid particles circulate in the bloodstream carrying cholesterol. Elevated levels are influenced by nutrition, genetics, physical activity, and metabolic status.",
            "recommendation": "Discuss these lipid values with your healthcare provider alongside lifestyle factors and overall health history."
        })

    # Pattern 11: Elevated Triglycerides
    if get_st("triglycerides") == "high":
        patterns.append({
            "pattern_id": "elevated_triglycerides",
            "name": "Elevated Triglyceride Levels",
            "severity": "attention",
            "biomarkers_involved": ["triglycerides"],
            "summary": "Triglycerides are elevated above the laboratory reference interval.",
            "educational_note": "Triglycerides are the primary storage form of fat in the body. Blood levels are sensitive to recent dietary intake, carbohydrate and alcohol consumption, and physical activity.",
            "recommendation": "Review nutrition, fasting duration prior to testing, and metabolic profile with your doctor."
        })

    # Pattern 12: Low HDL Cholesterol
    if get_st("hdl") == "low":
        patterns.append({
            "pattern_id": "low_hdl",
            "name": "Reduced HDL Cholesterol",
            "severity": "attention",
            "biomarkers_involved": ["hdl"],
            "summary": "HDL cholesterol is below the desired laboratory reference range.",
            "educational_note": "HDL (high-density lipoprotein) helps transport cholesterol away from tissues. Lower levels are often observed with sedentary lifestyle, smoking, or metabolic factors.",
            "recommendation": "Consult your clinician about lifestyle measures, physical activity, and dietary quality that support HDL levels."
        })

    return patterns


def generate_deterministic_report_summary(
    parsed_report: Dict[str, Any],
    patterns: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Builds a deterministic, template-driven report summary without an LLM.
    """
    report_type = parsed_report.get("report_type", "Lab Report")
    biomarkers = parsed_report.get("biomarkers", [])

    total = len(biomarkers)
    normal = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() == "normal")
    low = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() == "low")
    high = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() == "high")
    needs_review = sum(1 for bm in biomarkers if str(bm.get("status", "")).lower() in ("needs review", "unknown"))

    # Template narrative
    narrative_parts = []
    narrative_parts.append(f"Your {report_type} contains {total} analyzed parameter{'' if total == 1 else 's'}.")

    if normal == total:
        narrative_parts.append("All analyzed biomarkers are within their provided biological reference ranges.")
    else:
        findings = []
        if normal > 0:
            findings.append(f"{normal} within reference range")
        if low > 0:
            findings.append(f"{low} below range")
        if high > 0:
            findings.append(f"{high} above range")
        if needs_review > 0:
            findings.append(f"{needs_review} requiring clinical review")

        narrative_parts.append(f"Findings indicate {', '.join(findings)}.")

    if patterns:
        pattern_names = [p["name"] for p in patterns]
        narrative_parts.append(f"Detected pattern{'' if len(patterns) == 1 else 's'}: {', '.join(pattern_names)}.")
    elif normal == total:
        narrative_parts.append("No abnormal physiological patterns were detected.")

    return {
        "report_type": report_type,
        "narrative": " ".join(narrative_parts),
        "total_parameters": total,
        "normal": normal,
        "low": low,
        "high": high,
        "needs_review": needs_review,
        "abnormal_total": low + high,
        "patterns_count": len(patterns)
    }
