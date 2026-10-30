import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from app.database.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def to_utc_iso(dt: Optional[Any]) -> Optional[str]:
    """
    Converts a datetime object or ISO string to an explicit UTC ISO-8601 string
    with a '+00:00' or 'Z' timezone suffix.
    Ensures that SQLite naive datetimes are never misinterpreted as local browser time.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        clean = dt.strip()
        if not clean or clean.lower() == "none":
            return None
        if " " in clean and "T" not in clean:
            clean = clean.replace(" ", "T")
        if not (clean.endswith("Z") or re.search(r'[+-]\d{2}:\d{2}$', clean)):
            clean += "Z"
        return clean
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif not hasattr(dt, "tzinfo"):
        return str(dt)
    return dt.isoformat()


class HealthReport(Base):
    __tablename__ = "health_reports"

    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uploaded_at = Column(DateTime, default=get_utc_now)
    filename = Column(String, nullable=True)
    report_type = Column(String, nullable=True)
    overall_status = Column(String, nullable=True)
    abnormal_count = Column(Integer, default=0)
    report_json = Column(JSON, nullable=True)
    # SHA-256 hex digest of the uploaded file — used for duplicate detection
    file_hash = Column(Text, nullable=True, index=True)
    # Deterministic rule engine version that produced the stored interpretation
    interpretation_engine_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    saved_at = Column(DateTime, nullable=True)

    @property
    def saved_at_iso(self) -> Optional[str]:
        """Authoritative timestamp when the report was persisted to Health Vault (ISO-8601 string)."""
        dt = self.saved_at or self.created_at
        return to_utc_iso(dt)

    @property
    def saved_to_vault_at(self) -> Optional[str]:
        """Authoritative timestamp when the report was persisted to Health Vault (ISO-8601 string)."""
        return self.saved_at_iso

    @property
    def analyzed_at(self) -> Optional[str]:
        """Authoritative timestamp when the report was processed by the analysis pipeline."""
        if self.report_json and isinstance(self.report_json, dict):
            raw = self.report_json.get("analyzed_at") or (self.report_json.get("metadata") or {}).get("analyzed_at")
            return to_utc_iso(raw)
        return None
