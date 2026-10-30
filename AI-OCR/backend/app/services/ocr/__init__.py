import os
import sys
import time
import logging
import concurrent.futures
from typing import List, Dict, Any, Optional
from app.services.ocr.base_ocr import BaseOCRProvider
from app.services.ocr.rapidocr_provider import RapidOCRProvider

logger = logging.getLogger("sita.ocr")

_ocr_provider_instance: Optional[BaseOCRProvider] = None
_paddle_fallback_instance: Optional[BaseOCRProvider] = None


class OCRError(Exception):
    """Base exception for OCR processing failures."""
    pass


class OCRTimeoutError(OCRError):
    """Raised when OCR inference exceeds the configured timeout."""
    pass


def get_ocr_timeout_seconds() -> float:
    """
    Get configured OCR timeout in seconds. Defaults to 30.0 seconds.
    """
    try:
        return float(os.getenv("OCR_TIMEOUT_SECONDS", "30"))
    except ValueError:
        return 30.0


def is_fallback_enabled() -> bool:
    """
    Check if OCR fallback to PaddleOCR is enabled. Defaults to False in production.
    """
    return os.getenv("OCR_ENABLE_FALLBACK", "false").lower() in ("true", "1", "yes")


def is_compare_mode_enabled() -> bool:
    """
    Check if side-by-side OCR comparison mode is enabled. Defaults to False in production.
    """
    return os.getenv("OCR_COMPARE", "false").lower() in ("true", "1", "yes")


def get_ocr_provider() -> BaseOCRProvider:
    """
    Get the configured singleton OCR provider.
    Defaults to RapidOCR ONNX Runtime. Supports PaddleOCR if explicitly configured via OCR_PROVIDER=paddleocr.
    """
    global _ocr_provider_instance
    if _ocr_provider_instance is None:
        provider_name = os.getenv("OCR_PROVIDER", "rapidocr").lower()
        if provider_name == "paddleocr":
            try:
                from app.services.ocr.paddleocr_provider import PaddleOCRProvider
                _ocr_provider_instance = PaddleOCRProvider()
            except Exception as e:
                logger.warning(f"[OCR WARNING] Failed to initialize PaddleOCR ({e}), falling back to RapidOCR.")
                _ocr_provider_instance = RapidOCRProvider()
        else:
            _ocr_provider_instance = RapidOCRProvider()
    return _ocr_provider_instance


def get_paddle_fallback_provider() -> Optional[BaseOCRProvider]:
    """
    Get or create singleton PaddleOCR provider for comparison mode or emergency fallback.
    """
    global _paddle_fallback_instance
    if _paddle_fallback_instance is None:
        try:
            from app.services.ocr.paddleocr_provider import PaddleOCRProvider
            _paddle_fallback_instance = PaddleOCRProvider()
        except Exception as e:
            logger.warning(f"[OCR WARNING] PaddleOCR fallback provider unavailable: {e}")
            _paddle_fallback_instance = None
    return _paddle_fallback_instance


def get_ocr_health_info() -> Dict[str, Any]:
    """
    Returns sanitized OCR health and configuration status for health checks.
    """
    provider_name = os.getenv("OCR_PROVIDER", "rapidocr").lower()
    fallback_enabled = is_fallback_enabled()
    compare_enabled = is_compare_mode_enabled()
    timeout_sec = get_ocr_timeout_seconds()

    is_initialized = _ocr_provider_instance is not None
    provider_class = _ocr_provider_instance.__class__.__name__ if is_initialized else ("RapidOCRProvider" if provider_name == "rapidocr" else "PaddleOCRProvider")

    return {
        "provider": "RapidOCR" if "rapid" in provider_class.lower() else "PaddleOCR",
        "provider_class": provider_class,
        "status": "Ready" if is_initialized else "Standby (Lazy Init)",
        "model_initialized": is_initialized,
        "fallback_enabled": fallback_enabled,
        "compare_mode": compare_enabled,
        "timeout_seconds": timeout_sec
    }


def _run_with_timeout(func, arg, timeout_sec: float) -> Any:
    """
    Executes func(arg) in a thread with a hard timeout.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, arg)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            raise OCRTimeoutError(f"OCR inference exceeded timeout of {timeout_sec}s")


def extract_with_provider_resilience(image_input: Any, primary_provider: Optional[BaseOCRProvider] = None) -> List[Dict[str, Any]]:
    """
    Extracts text using primary provider (RapidOCR) with timeout protection.
    If it fails or times out:
      - If fallback is enabled (OCR_ENABLE_FALLBACK=true): attempts PaddleOCR fallback.
      - If fallback is disabled (default production): raises OCRError / OCRTimeoutError.
    Supports OCR_COMPARE=true development mode for A/B comparison.
    """
    provider = primary_provider or get_ocr_provider()
    timeout_sec = get_ocr_timeout_seconds()
    fallback_allowed = is_fallback_enabled()
    compare_mode = is_compare_mode_enabled()

    primary_lines: List[Dict[str, Any]] = []
    primary_failed = False
    last_error: Optional[Exception] = None

    try:
        if timeout_sec > 0:
            primary_lines = _run_with_timeout(provider.extract_from_image, image_input, timeout_sec)
        else:
            primary_lines = provider.extract_from_image(image_input)
    except OCRTimeoutError as te:
        logger.error(f"[OCR TIMEOUT] Primary provider {provider.__class__.__name__} timed out after {timeout_sec}s: {te}")
        primary_failed = True
        last_error = te
    except Exception as e:
        logger.error(f"[OCR ERROR] Primary provider {provider.__class__.__name__} failed: {e}", exc_info=True)
        primary_failed = True
        last_error = e

    # Fallback if primary failed AND fallback is explicitly allowed
    if primary_failed or not primary_lines:
        paddle_cls = getattr(sys.modules.get("app.services.ocr.paddleocr_provider"), "PaddleOCRProvider", None)
        is_already_paddle = paddle_cls and isinstance(provider, paddle_cls)

        if fallback_allowed and not is_already_paddle:
            fallback_provider = get_paddle_fallback_provider()
            if fallback_provider:
                logger.warning("[OCR RESILIENCE] RapidOCR failed/timed out. Attempting PaddleOCR fallback extraction...")
                try:
                    if timeout_sec > 0:
                        primary_lines = _run_with_timeout(fallback_provider.extract_from_image, image_input, timeout_sec * 4) # Allow more time for Paddle if fallback
                    else:
                        primary_lines = fallback_provider.extract_from_image(image_input)
                    logger.info(f"[OCR RESILIENCE] PaddleOCR fallback succeeded with {len(primary_lines)} lines.")
                    last_error = None
                except Exception as fb_err:
                    logger.error(f"[OCR ERROR] PaddleOCR fallback also failed: {fb_err}", exc_info=True)
                    last_error = fb_err
        else:
            if primary_failed:
                if isinstance(last_error, OCRTimeoutError):
                    raise last_error
                raise OCRError(f"OCR extraction failed: {last_error}")

    # Optional Comparison Mode (for development / debugging only)
    if compare_mode and not primary_failed:
        fallback_provider = get_paddle_fallback_provider()
        if fallback_provider:
            try:
                paddle_lines = fallback_provider.extract_from_image(image_input)
                print("\n" + "=" * 50)
                print("[OCR COMPARISON MODE: RapidOCR vs PaddleOCR]")
                print(f"RapidOCR lines:  {len(primary_lines)}")
                print(f"PaddleOCR lines: {len(paddle_lines)}")
                avg_rapid_conf = sum(l.get("confidence", 0) for l in primary_lines) / len(primary_lines) if primary_lines else 0
                avg_paddle_conf = sum(l.get("confidence", 0) for l in paddle_lines) / len(paddle_lines) if paddle_lines else 0
                print(f"RapidOCR Avg Confidence:  {avg_rapid_conf:.3f}")
                print(f"PaddleOCR Avg Confidence: {avg_paddle_conf:.3f}")
                print("=" * 50 + "\n")
            except Exception as comp_err:
                print(f"[OCR COMPARISON WARNING] Failed to run comparison provider: {comp_err}")

    return primary_lines
