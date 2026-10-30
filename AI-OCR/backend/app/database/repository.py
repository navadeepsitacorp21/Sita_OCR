import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.database import engine, Base
from app.database.models import HealthReport

# Ensure tables are created
Base.metadata.create_all(bind=engine)


def create_report(db: Session, report_payload: Dict[str, Any]) -> HealthReport:
    """
    Store a parsed laboratory report in the local Health Vault repository.
    Extracts report metadata and serializes full payload in report_json.
    """
    report_id = report_payload.get("report_id") or str(uuid.uuid4())
    uploaded_at = report_payload.get("uploaded_at") or datetime.now(timezone.utc)
    filename = report_payload.get("filename")

    classification = report_payload.get("classification") or {}
    parsed_report = report_payload.get("parsed_report") or {}
    health_summary = report_payload.get("health_summary") or {}

    report_type = (
        report_payload.get("report_type")
        or classification.get("report_type")
        or parsed_report.get("report_type")
        or "UNKNOWN"
    )
    overall_status = (
        report_payload.get("overall_status")
        or health_summary.get("overall_status")
        or "Unknown"
    )
    abnormal_count = (
        report_payload.get("abnormal_count")
        if report_payload.get("abnormal_count") is not None
        else health_summary.get("abnormal_count", 0)
    )

    report_json = report_payload.get("report_json") or report_payload

    db_report = HealthReport(
        report_id=report_id,
        uploaded_at=uploaded_at,
        filename=filename,
        report_type=report_type,
        overall_status=overall_status,
        abnormal_count=abnormal_count,
        report_json=report_json,
        created_at=datetime.now(timezone.utc)
    )

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def get_report(db: Session, report_id: str) -> Optional[HealthReport]:
    """Retrieve a single health report by report_id."""
    return db.query(HealthReport).filter(HealthReport.report_id == report_id).first()


def list_reports(db: Session) -> List[HealthReport]:
    """List all health reports ordered by newest uploaded_at first."""
    return db.query(HealthReport).order_by(HealthReport.uploaded_at.desc()).all()


def delete_report(db: Session, report_id: str) -> bool:
    """Delete a health report by report_id. Returns True if deleted, False if not found."""
    report = get_report(db, report_id)
    if not report:
        return False
    db.delete(report)
    db.commit()
    return True
