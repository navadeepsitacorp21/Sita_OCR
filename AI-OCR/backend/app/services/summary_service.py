from typing import List
from app.models.biomarker_models import Biomarker

class SummaryService:
    def generate_summary(self, biomarkers: List[Biomarker], report_type: str) -> str:
        """
        Generate summary highlighting abnormal values and key clinical insights.
        """
        abnormal = [b.name for b in biomarkers if b.is_abnormal]
        if abnormal:
            return f"{report_type}: Flagged out-of-range values in {', '.join(abnormal)}."
        return f"{report_type}: All analyzed biomarkers are within healthy reference ranges."
