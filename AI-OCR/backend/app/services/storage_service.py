import uuid
from datetime import datetime
from typing import List, Optional
from app.models.report_models import ReportDetail, ReportUploadResponse
from app.services.ocr_service import OCRService
from app.services.classifier_service import ClassifierService
from app.services.parser_service import ParserService
from app.services.summary_service import SummaryService

class StorageService:
    def __init__(self):
        self.ocr_service = OCRService()
        self.classifier = ClassifierService()
        self.parser = ParserService()
        self.summarizer = SummaryService()
        self._db = {}

    async def save_and_process_report(self, filename: str, content: bytes) -> ReportUploadResponse:
        report_id = str(uuid.uuid4())
        raw_text = await self.ocr_service.extract_text(content, filename)
        report_type, confidence = self.classifier.classify_report(raw_text)
        biomarkers = self.parser.parse_biomarkers(raw_text, report_type)
        summary = self.summarizer.generate_summary(biomarkers, report_type)
        created_at = datetime.utcnow().isoformat()

        report_detail = ReportDetail(
            report_id=report_id,
            file_name=filename,
            report_type=report_type,
            raw_text=raw_text,
            biomarkers=biomarkers,
            summary=summary,
            metadata={"confidence": confidence, "created_at": created_at}
        )
        self._db[report_id] = report_detail

        return ReportUploadResponse(
            report_id=report_id,
            file_name=filename,
            report_type=report_type,
            confidence_score=confidence,
            biomarkers=biomarkers,
            summary=summary,
            created_at=created_at
        )

    async def get_all_reports(self) -> List[ReportDetail]:
        return list(self._db.values())

    async def get_report_by_id(self, report_id: str) -> Optional[ReportDetail]:
        return self._db.get(report_id)
