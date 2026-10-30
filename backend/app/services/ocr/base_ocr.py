from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseOCRProvider(ABC):
    """
    Abstract base class for all OCR Providers.
    Defines a standard extraction interface returning normalized structured OCR lines.
    """

    @abstractmethod
    def extract_from_image(self, image_input: Any) -> List[Dict[str, Any]]:
        """
        Extract text from an image path or numpy ndarray.

        Returns a list of dicts:
        [
            {
                "text": str,
                "confidence": float,
                "bbox": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] # or [x1, y1, x2, y2]
            },
            ...
        ]
        """
        pass
