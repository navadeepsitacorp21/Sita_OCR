from fastapi import APIRouter
from app.services.ocr import get_ocr_health_info

router = APIRouter(tags=["Health"])

@router.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {
        "status": "healthy",
        "service": "SITA OCR Engine"
    }

@router.get("/health/ocr")
def ocr_health():
    """
    Returns OCR backend health, initialized status, timeout settings, and fallback configuration.
    """
    return {
        "status": "healthy",
        "service": "SITA OCR Engine",
        "ocr": get_ocr_health_info()
    }