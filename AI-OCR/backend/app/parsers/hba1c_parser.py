from typing import Dict, Any, List, Optional
from app.parsers.base_parser import BaseParser


class HbA1cParser(BaseParser):
    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        from app.services.parser_service import parser_service
        res = parser_service._parse_category_report(
            category="DIABETES_PROFILE",
            report_type="DIABETES_PROFILE",
            parser_version="1.2.0",
            ocr_text=ocr_text,
            ocr_lines=ocr_lines,
            default_categories={
                "blood_glucose": [],
                "long_term_control": []
            }
        )
        res["hospital"] = hospital
        return res
