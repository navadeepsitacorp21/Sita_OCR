from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, list_reports, get_report, delete_report
from app.database.models import to_utc_iso

router = APIRouter(tags=["Health Vault"])


from app.services.trend_service import get_effective_report_date
from app.services.medical_explanation_engine import generate_medical_explanation

@router.get("/health-vault/reports")
def get_health_vault_timeline(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieve lightweight timeline metadata for all saved reports in the Health Vault.
    Organized according to actual medical report date when available, falling back
    to uploaded_at for chronological medical history.
    """
    reports = list_reports(db)
    # Sort chronologically by effective medical report date (newest medical date first)
    sorted_reports = sorted(reports, key=get_effective_report_date, reverse=True)

    items = []
    for r in sorted_reports:
        uploaded_at_str = (
            r.uploaded_at.isoformat()
            if hasattr(r.uploaded_at, "isoformat")
            else str(r.uploaded_at)
        )
        r_json = r.report_json or {}
        p_report = r_json.get("parsed_report") or r_json
        r_meta = (
            p_report.get("report")
            or (p_report.get("metadata") or {}).get("report")
            or (r_json.get("metadata") or {}).get("report")
            or r_json.get("report")
            or {}
        )
        rep_date = (
            r_json.get("report_date")
            or r_meta.get("report_date")
            or r_meta.get("collection_date")
            or r_meta.get("reported_date")
            or r_meta.get("received_date")
            or r_meta.get("ordered_date")
        )
        coll_date = r_json.get("collection_date") or r_meta.get("collection_date")
        rep_on = r_json.get("reported_date") or r_meta.get("reported_date")

        total_bms = (
            p_report.get("biomarkers_found")
            or len(p_report.get("biomarkers", []))
            or 0
        )

        saved_at_str = to_utc_iso(r.saved_at or r.created_at or r.uploaded_at)
        analyzed_at_raw = (
            r_json.get("analyzed_at")
            or (r_json.get("metadata") or {}).get("analyzed_at")
        )
        analyzed_at_str = to_utc_iso(analyzed_at_raw) if analyzed_at_raw else saved_at_str

        items.append({
            "report_id": r.report_id,
            "uploaded_at": saved_at_str,
            "saved_at": saved_at_str,
            "saved_to_vault_at": saved_at_str,
            "analyzed_at": analyzed_at_str,
            "report_date": rep_date,
            "collection_date": coll_date,
            "reported_date": rep_on,
            "filename": r.filename,
            "report_type": r.report_type,
            "overall_status": r.overall_status,
            "abnormal_count": r.abnormal_count,
            "biomarkers_found": total_bms,
            "total_parameters": total_bms
        })

    return {
        "count": len(items),
        "reports": items
    }


@router.get("/health-vault/reports/{report_id}")
def get_health_vault_report_detail(
    report_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve complete stored report data including full parsed payload and health highlights.
    """
    record = get_report(db, report_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Health report with ID '{report_id}' was not found."
        )

    uploaded_at_str = (
        record.uploaded_at.isoformat()
        if hasattr(record.uploaded_at, "isoformat")
        else str(record.uploaded_at)
    )

    report_dict = dict(record.report_json) if record.report_json else {}
    if "explanation" not in report_dict:
        parsed = report_dict.get("parsed_report") or report_dict
        parsed_bms = (report_dict.get("analysis") or {}).get("biomarkers") or parsed.get("biomarkers") or []
        parsed_pats = (report_dict.get("analysis") or {}).get("patterns") or parsed.get("patterns") or []
        report_dict["explanation"] = generate_medical_explanation(
            report_type=record.report_type,
            biomarkers=parsed_bms,
            patterns=parsed_pats,
            patient_gender=None
        )

    saved_at_str = to_utc_iso(record.saved_at or record.created_at or record.uploaded_at)
    analyzed_at_raw = (
        report_dict.get("analyzed_at")
        or (report_dict.get("metadata") or {}).get("analyzed_at")
    )
    analyzed_at_str = to_utc_iso(analyzed_at_raw) if analyzed_at_raw else saved_at_str

    return {
        "report_id": record.report_id,
        "uploaded_at": saved_at_str,
        "saved_at": saved_at_str,
        "saved_to_vault_at": saved_at_str,
        "analyzed_at": analyzed_at_str,
        "report_date": report_dict.get("report_date"),
        "filename": record.filename,
        "report": report_dict
    }


@router.delete("/health-vault/reports/{report_id}")
def delete_health_vault_report(
    report_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete a saved health report from the Health Vault by ID.
    """
    deleted = delete_report(db, report_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Health report with ID '{report_id}' was not found."
        )

    return {
        "report_id": report_id,
        "deleted": True
    }
