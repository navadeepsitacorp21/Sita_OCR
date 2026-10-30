from typing import Dict, Any, List, Optional
from app.parsers.base_parser import BaseParser


class ThyroidParser(BaseParser):
    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        from app.services.parser_service import parser_service
        res = parser_service._parse_category_report(
            category="THYROID_PROFILE",
            report_type="THYROID_PROFILE",
            parser_version="1.2.0",
            ocr_text=ocr_text,
            ocr_lines=ocr_lines,
            default_categories={
                "pituitary_hormones": [],
                "thyroid_hormones": []
            }
        )
        res["hospital"] = hospital
        return res
