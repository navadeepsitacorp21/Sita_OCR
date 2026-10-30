from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.models.biomarker_models import Biomarker

class ReportUploadResponse(BaseModel):
    report_id: str
    file_name: str
    report_type: str
    confidence_score: float
    biomarkers: List[Biomarker]
    summary: str
    created_at: str

class ReportDetail(BaseModel):
    report_id: str
    file_name: str
    report_type: str
    raw_text: str
    biomarkers: List[Biomarker]
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
