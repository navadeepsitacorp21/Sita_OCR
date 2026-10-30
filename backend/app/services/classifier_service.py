import json
import os
import re
from typing import Dict, Any, List, Optional
from app.utils.text_utils import clean_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT_PATTERNS_PATH = os.path.join(BASE_DIR, "data", "report_patterns.json")
CLASSIFIER_VERSION = "1.0.0"


class ClassifierService:
    def __init__(self, patterns_path: str = REPORT_PATTERNS_PATH):
        self.patterns = self._load_patterns(patterns_path)

    def _load_patterns(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def classify_report(self, ocr_text: str) -> Dict[str, Any]:
        """
        Classify document text deterministically into laboratory report categories
        using keyword pattern matching and threshold scoring.
        """
        if not ocr_text:
            return self._unknown_response()

        cleaned_text = clean_text(ocr_text).lower()
        best_match = None
        best_count = 0
        best_priority = 0
        best_keywords = []
        best_min_matches = 0

        for report_type, config in self.patterns.items():
            keywords = config.get("keywords", [])
            min_matches = config.get("minimum_matches", 2)
            priority = config.get("priority", 1)

            matched = []
            for kw in keywords:
                kw_lower = kw.lower()
                # Check for word boundary match or substring for multi-word phrases
                if " " in kw_lower or "/" in kw_lower:
                    if kw_lower in cleaned_text:
                        matched.append(kw)
                else:
                    pattern = r'\b' + re.escape(kw_lower) + r'\b'
                    if re.search(pattern, cleaned_text):
                        matched.append(kw)

            # Deduplicate matched keywords
            unique_matched = list(dict.fromkeys(matched))
            match_count = len(unique_matched)

            if match_count >= min_matches:
                # Rank by match count first, then priority
                if (match_count > best_count) or (match_count == best_count and priority > best_priority):
                    best_match = report_type
                    best_count = match_count
                    best_priority = priority
                    best_keywords = unique_matched
                    best_min_matches = min_matches

        if best_match is not None:
            # Deterministic confidence scaling
            base_conf = 0.70
            scale_step = 0.08
            conf = min(base_conf + (best_count - best_min_matches) * scale_step, 0.98)
            
            return {
                "report_type": best_match,
                "confidence": round(conf, 2),
                "matched_keywords": best_keywords,
                "matched_keyword_count": best_count,
                "minimum_required_matches": best_min_matches,
                "classifier_version": CLASSIFIER_VERSION
            }

        return self._unknown_response()

    def _unknown_response(self) -> Dict[str, Any]:
        return {
            "report_type": "UNKNOWN",
            "confidence": 0.0,
            "matched_keywords": [],
            "matched_keyword_count": 0,
            "minimum_required_matches": 0,
            "classifier_version": CLASSIFIER_VERSION
        }


# Singleton classifier instance
classifier_service = ClassifierService()


def classify_report(ocr_text: str) -> Dict[str, Any]:
    return classifier_service.classify_report(ocr_text)
