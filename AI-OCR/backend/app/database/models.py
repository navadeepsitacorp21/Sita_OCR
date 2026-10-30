import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON
from app.database.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class HealthReport(Base):
    __tablename__ = "health_reports"

    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uploaded_at = Column(DateTime, default=get_utc_now)
    filename = Column(String, nullable=True)
    report_type = Column(String, nullable=True)
    overall_status = Column(String, nullable=True)
    abnormal_count = Column(Integer, default=0)
    report_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
