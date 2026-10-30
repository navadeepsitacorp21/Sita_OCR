import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.database import engine, Base
from app.database.models import HealthReport

# Ensure tables are created
Base.metadata.create_all(bind=engine)

# Auto-migrate SQLite schema if saved_at column is missing
try:
    from sqlalchemy import text
    with engine.connect() as _conn:
        _res = _conn.execute(text("PRAGMA table_info(health_reports)"))
        _cols = [row[1] for row in _res.fetchall()]
        if "saved_at" not in _cols and "report_id" in _cols:
            _conn.execute(text("ALTER TABLE health_reports ADD COLUMN saved_at DATETIME"))
            _conn.commit()
except Exception:
    pass


def create_report(db: Session, report_payload: Dict[str, Any]) -> HealthReport:
    """
    Store a parsed laboratory report in the local Health Vault repository.
    Extracts report metadata and serializes full payload in report_json.
    """
    report_id = report_payload.get("report_id") or str(uuid.uuid4())
    uploaded_at_val = report_payload.get("uploaded_at")
    if isinstance(uploaded_at_val, str):
        try:
            uploaded_at = datetime.fromisoformat(uploaded_at_val.replace("Z", "+00:00"))
        except Exception:
            uploaded_at = datetime.now(timezone.utc)
    elif isinstance(uploaded_at_val, datetime):
        uploaded_at = uploaded_at_val
    else:
        uploaded_at = datetime.now(timezone.utc)

    saved_at_val = report_payload.get("saved_at") or report_payload.get("saved_to_vault_at")
    if isinstance(saved_at_val, str):
        try:
            saved_at = datetime.fromisoformat(saved_at_val.replace("Z", "+00:00"))
        except Exception:
            saved_at = datetime.now(timezone.utc)
    elif isinstance(saved_at_val, datetime):
        saved_at = saved_at_val
    else:
        saved_at = datetime.now(timezone.utc)

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
        file_hash=report_payload.get("file_hash"),
        interpretation_engine_version=report_payload.get("interpretation_engine_version"),
        created_at=saved_at,
        saved_at=saved_at
    )

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def get_report(db: Session, report_id: str) -> Optional[HealthReport]:
    """Retrieve a single health report by report_id."""
    return db.query(HealthReport).filter(HealthReport.report_id == report_id).first()


def get_report_by_hash(db: Session, file_hash: str) -> Optional[HealthReport]:
    """Retrieve the most recent vault record whose uploaded file SHA-256 matches."""
    return (
        db.query(HealthReport)
        .filter(HealthReport.file_hash == file_hash)
        .order_by(HealthReport.uploaded_at.desc())
        .first()
    )


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
