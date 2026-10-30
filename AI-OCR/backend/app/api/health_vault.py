from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, list_reports, get_report, delete_report

router = APIRouter(tags=["Health Vault"])


@router.get("/health-vault/reports")
def get_health_vault_timeline(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieve lightweight timeline metadata for all saved reports in the Health Vault.
    Ordered newest upload first.
    """
    reports = list_reports(db)
    items = []
    for r in reports:
        uploaded_at_str = (
            r.uploaded_at.isoformat()
            if hasattr(r.uploaded_at, "isoformat")
            else str(r.uploaded_at)
        )
        items.append({
            "report_id": r.report_id,
            "uploaded_at": uploaded_at_str,
            "filename": r.filename,
            "report_type": r.report_type,
            "overall_status": r.overall_status,
            "abnormal_count": r.abnormal_count
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

    return {
        "report_id": record.report_id,
        "uploaded_at": uploaded_at_str,
        "filename": record.filename,
        "report": record.report_json
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
