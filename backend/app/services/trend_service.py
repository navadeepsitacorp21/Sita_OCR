import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.database.models import HealthReport

from datetime import datetime, timezone
import re

logger = logging.getLogger("sita.trend_service")


def _parse_report_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string into a datetime object for comparison."""
    if not date_str:
        return None
    cleaned = re.sub(r'[\)\(\]\[]', '/', str(date_str)).strip()
    # Try ISO YYYY-MM-DD
    m_iso = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})', cleaned)
    if m_iso:
        try:
            return datetime(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)), tzinfo=timezone.utc)
        except Exception:
            pass
    # Try DD/MM/YYYY
    m_dmy = re.match(r'^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', cleaned)
    if m_dmy:
        try:
            y = int(m_dmy.group(3))
            if y < 100:
                y += 2000
            return datetime(y, int(m_dmy.group(2)), int(m_dmy.group(1)), tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def get_effective_report_date(report: HealthReport) -> datetime:
    """
    Returns the actual medical report/collection datetime if present in report_json,
    otherwise falls back to uploaded_at timestamp.
    """
    r_json = report.report_json or {}
    meta = r_json.get("metadata") or {}
    report_meta = meta.get("report") or {}
    
    # Try report_date or collection_date
    r_date_str = (
        r_json.get("report_date")
        or report_meta.get("report_date")
        or report_meta.get("collection_date")
        or (r_json.get("parsed_report") or {}).get("metadata", {}).get("report", {}).get("report_date")
    )

    if r_date_str:
        parsed_dt = _parse_report_datetime(r_date_str)
        if parsed_dt:
            return parsed_dt

    if hasattr(report.uploaded_at, "tzinfo") and report.uploaded_at.tzinfo:
        return report.uploaded_at
    elif report.uploaded_at:
        return report.uploaded_at.replace(tzinfo=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


def compute_biomarker_trends(
    db: Session,
    current_biomarkers: List[Dict[str, Any]],
    current_report_type: str,
    exclude_report_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deterministically computes longitudinal trends for biomarkers by comparing
    current values against previous reports in the Health Vault.
    Uses actual medical report/collection dates when available so chronology
    reflects clinical history rather than upload order.
    No LLM is used.
    """
    trends: Dict[str, Any] = {}
    if not current_biomarkers:
        return trends

    try:
        # Retrieve previous reports of matching report_type
        query = db.query(HealthReport).filter(HealthReport.report_type == current_report_type)
        if exclude_report_id:
            query = query.filter(HealthReport.report_id != exclude_report_id)

        all_past = query.all()
        if not all_past:
            return trends

        # Sort reports chronologically by their effective medical date (newest first)
        past_reports = sorted(all_past, key=get_effective_report_date, reverse=True)[:10]

        # Build chronological history per biomarker key
        # past_reports is newest first: past_reports[0] is most recent prior report
        for bm in current_biomarkers:
            k = bm.get("key", "").lower()
            cur_val = bm.get("value")
            cur_unit = bm.get("unit") or ""
            if not k or cur_val is None:
                continue

            # Gather historical values
            history: List[Dict[str, Any]] = []
            for r in past_reports:
                r_json = r.report_json or {}
                parsed = r_json.get("parsed_report") or {}
                bms = parsed.get("biomarkers", [])
                
                # Check for extracted report date
                r_meta = (parsed.get("metadata") or {}).get("report") or (r_json.get("metadata") or {}).get("report") or {}
                rep_date = r_json.get("report_date") or r_meta.get("report_date") or r_meta.get("collection_date")

                for past_bm in bms:
                    if past_bm.get("key", "").lower() == k and past_bm.get("value") is not None:
                        history.append({
                            "report_id": r.report_id,
                            "report_date": rep_date,
                            "uploaded_at": r.uploaded_at.isoformat() if hasattr(r.uploaded_at, "isoformat") else str(r.uploaded_at),
                            "value": past_bm.get("value"),
                            "unit": past_bm.get("unit") or cur_unit,
                            "status": past_bm.get("status", "Unknown")
                        })
                        break

            if not history:
                continue

            # Compare with immediate previous report
            prev = history[0]
            prev_val = prev["value"]
            diff = round(cur_val - prev_val, 2)
            pct_change = round(((cur_val - prev_val) / abs(prev_val)) * 100, 1) if prev_val != 0 else 0.0

            if diff > 0:
                direction = "increased"
                arrow = "↑"
                summary_text = f"{bm.get('name', k.title())} increased from {prev_val} {cur_unit} to {cur_val} {cur_unit} (+{abs(diff)} {cur_unit})."
            elif diff < 0:
                direction = "decreased"
                arrow = "↓"
                summary_text = f"{bm.get('name', k.title())} decreased from {prev_val} {cur_unit} to {cur_val} {cur_unit} (-{abs(diff)} {cur_unit})."
            else:
                direction = "stable"
                arrow = "→"
                summary_text = f"{bm.get('name', k.title())} remained steady at {cur_val} {cur_unit}."

            # Multi-report longitudinal trend detection (across 3 or more reports)
            multi_trend = None
            if len(history) >= 2:
                # History is: [prev1, prev2, ...] and current is cur_val
                # Chronological series: [prev2, prev1, cur_val]
                vals = [history[1]["value"], history[0]["value"], cur_val]
                if vals[0] < vals[1] < vals[2]:
                    multi_trend = f"{bm.get('name', k.title())} has consistently increased across the last 3 recorded reports."
                elif vals[0] > vals[1] > vals[2]:
                    multi_trend = f"{bm.get('name', k.title())} has consistently decreased across the last 3 recorded reports."

            trends[k] = {
                "key": k,
                "name": bm.get("name", k.title()),
                "current_value": cur_val,
                "previous_value": prev_val,
                "unit": cur_unit,
                "diff": diff,
                "percentage_change": pct_change,
                "direction": direction,
                "arrow": arrow,
                "summary": summary_text,
                "multi_report_trend": multi_trend,
                "previous_date": prev.get("report_date") or prev["uploaded_at"],
                "previous_report_date": prev.get("report_date"),
                "previous_uploaded_at": prev["uploaded_at"],
                "data_points_count": len(history) + 1
            }

    except Exception as e:
        logger.error(f"Error computing biomarker trends: {e}")

    return trends
