from typing import Dict, Any, List
from app.services.biomarker_family_service import group_primary_biomarkers


def generate_health_highlights(parsed_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate deterministic health highlights from abnormal primary biomarkers in a parsed report.
    Produces UI-ready highlight cards without diagnosis or external LLMs.
    Filters out secondary family biomarkers (such as Vitamin D2/D3 when Vitamin D Total exists).
    """
    raw_biomarkers = parsed_report.get("biomarkers", [])
    primary_biomarkers = group_primary_biomarkers(raw_biomarkers)
    highlights: List[Dict[str, Any]] = []

    for bm in primary_biomarkers:
        status = str(bm.get("status", "")).strip()
        status_lower = status.lower()

        if status_lower not in ("high", "low"):
            continue

        name = bm.get("name") or bm.get("key") or "Biomarker"
        if status_lower == "high":
            severity = "critical"
            title = f"{name} is above the normal range."
            norm_status = "High"
        else:
            severity = "warning"
            title = f"{name} is below the normal range."
            norm_status = "Low"

        card = {
            "key": bm.get("key", ""),
            "name": name,
            "status": norm_status,
            "severity": severity,
            "title": title,
            "reference_range": bm.get("reference_range", ""),
            "value": bm.get("value"),
            "unit": bm.get("unit", "")
        }

        if bm.get("clinical_stage"):
            card["clinical_stage"] = bm["clinical_stage"]

        highlights.append(card)

    return {
        "highlights": highlights
    }
