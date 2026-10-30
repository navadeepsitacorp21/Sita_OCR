from typing import Dict, Any, List
from app.services.biomarker_family_service import group_primary_biomarkers


def generate_health_summary(parsed_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 10: Health Summary Improvements
    Do not include "Needs Review" biomarkers in abnormal counts.
    Returns total, normal, low, high, needs_review, unknown.
    """
    report_type = parsed_report.get("report_type", "UNKNOWN")
    raw_biomarkers = parsed_report.get("biomarkers", [])
    primary_biomarkers = group_primary_biomarkers(raw_biomarkers)

    normal_count = 0
    high_count = 0
    low_count = 0
    needs_review_count = 0
    unknown_count = 0
    abnormal_biomarkers: List[Dict[str, str]] = []

    for bm in primary_biomarkers:
        status = str(bm.get("status", "Unknown")).strip()
        status_lower = status.lower()

        if status == "Needs Review":
            needs_review_count += 1
        elif status_lower == "normal":
            normal_count += 1
        elif status_lower == "high":
            high_count += 1
            abnormal_biomarkers.append({
                "key": bm.get("key", ""),
                "name": bm.get("name", ""),
                "status": "High"
            })
        elif status_lower == "low":
            low_count += 1
            abnormal_biomarkers.append({
                "key": bm.get("key", ""),
                "name": bm.get("name", ""),
                "status": "Low"
            })
        else:
            unknown_count += 1

    total_biomarkers = len(raw_biomarkers)
    abnormal_count = high_count + low_count

    if len(primary_biomarkers) == 0 or unknown_count == len(primary_biomarkers):
        overall_status = "Incomplete Report"
    elif abnormal_count == 0:
        overall_status = "Healthy"
    elif 1 <= abnormal_count <= 2:
        overall_status = "Needs Attention"
    else:
        overall_status = "Multiple Abnormalities"

    res = {
        "overall_status": overall_status,
        "report_type": report_type,
        "total_biomarkers": total_biomarkers,
        "normal_biomarkers": normal_count,
        "high_biomarkers": high_count,
        "low_biomarkers": low_count,
        "needs_review_biomarkers": needs_review_count,
        "unknown_biomarkers": unknown_count,
        "abnormal_count": abnormal_count,
        "abnormal_biomarkers": abnormal_biomarkers,
        "summary": {
            "total": total_biomarkers,
            "normal": normal_count,
            "low": low_count,
            "high": high_count,
            "needs_review": needs_review_count,
            "unknown": unknown_count
        }
    }
    return res
