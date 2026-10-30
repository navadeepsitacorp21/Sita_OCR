import os
import pytest
from app.services.ocr import (
    get_ocr_provider,
    get_ocr_health_info,
    extract_with_provider_resilience,
    OCRError,
    OCRTimeoutError,
    _run_with_timeout
)
from app.services.ocr.base_ocr import BaseOCRProvider


class SlowMockOCRProvider(BaseOCRProvider):
    def extract_from_image(self, image_input):
        import time
        time.sleep(1.5)
        return [{"text": "Mock Slow Line", "confidence": 0.99, "bbox": []}]


class FailingMockOCRProvider(BaseOCRProvider):
    def extract_from_image(self, image_input):
        raise RuntimeError("Simulated OCR Model Failure")


def test_ocr_health_endpoint_contract():
    health_info = get_ocr_health_info()
    assert "provider" in health_info
    assert "status" in health_info
    assert "model_initialized" in health_info
    assert "fallback_enabled" in health_info
    assert "compare_mode" in health_info
    assert "timeout_seconds" in health_info
    assert health_info["provider"] == "RapidOCR"


def test_ocr_timeout_enforcement():
    slow_provider = SlowMockOCRProvider()
    with pytest.raises(OCRTimeoutError):
        _run_with_timeout(slow_provider.extract_from_image, "dummy_path", timeout_sec=0.2)


def test_ocr_resilience_fallback_disabled_raises_error(monkeypatch):
    monkeypatch.setenv("OCR_ENABLE_FALLBACK", "false")
    failing_provider = FailingMockOCRProvider()

    with pytest.raises(OCRError):
        extract_with_provider_resilience("dummy_path", primary_provider=failing_provider)
