from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseParser(ABC):
    """
    Abstract Base Class for all category-specific lab report parsers in SITA OCR Engine v1.2.0.
    """

    @abstractmethod
    def parse(
        self,
        ocr_text: str,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        hospital: str = "generic"
    ) -> Dict[str, Any]:
        """
        Parse raw OCR text into structured Health Vault JSON payload.
        """
        pass
