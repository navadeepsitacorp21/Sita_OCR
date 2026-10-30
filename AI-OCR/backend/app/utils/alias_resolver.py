import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_ALIASES_PATH = os.path.join(BASE_DIR, "data", "biomarker_aliases.json")
DEFAULT_REF_PATH = os.path.join(BASE_DIR, "data", "biomarker_reference.json")

# Deterministic OCR cleanup corrections
OCR_CLEANUP_RULES = [
    (r'\bH\s*\.?\s*B\b', 'hb'),
    (r'\bH\s*\.?\s*G\s*\.?\s*B\b', 'hgb'),
    (r'\bW\s*\.?\s*B\s*\.?\s*C\b', 'wbc'),
    (r'\bR\s*\.?\s*B\s*\.?\s*C\b', 'rbc'),
    (r'\bP\s*\.?\s*L\s*\.?\s*T\b', 'plt'),
    (r'\bP\s*\.?\s*C\s*\.?\s*V\b', 'pcv'),
    (r'\bH\s*\.?\s*C\s*\.?\s*T\b', 'hct'),
    (r'\bPlate\s*lets\b', 'platelets'),
    (r'\bPlate\s*let\b', 'platelet'),
    (r'\bBilirubln\b', 'bilirubin'),
    (r'\bHaemoglobin\b', 'haemoglobin'),
    (r'\bNeut\s*%', 'neut %'),
    (r'\bLymph\s*%', 'lymph %'),
    (r'\bMono\s*%', 'mono %'),
    (r'\bEos\s*%', 'eos %'),
    (r'\bBaso\s*%', 'baso %'),
    (r'\bNeutrophil\s*%', 'neutrophil %'),
    (r'\bLymphocyte\s*%', 'lymphocyte %'),
    (r'\bMonocyte\s*%', 'monocyte %'),
    (r'\bEosinophil\s*%', 'eosinophil %'),
    (r'\bBasophil\s*%', 'basophil %'),
    (r'\bcalclum\b', 'calcium'),
    (r'\bcalcum\b', 'calcium'),
    (r'\bphosphorous\b', 'phosphorus'),
    (r'\bchlorlde\b', 'chloride'),
    (r'\bmagneslum\b', 'magnesium'),
    (r'\bcloride\b', 'chloride'),
    (r'\bvit\s*\.?\s*b12\b', 'vitamin b12'),
    (r'\bvit\s*\.?\s*b9\b', 'vitamin b9'),
    (r'\bvit\s*\.?\s*b6\b', 'vitamin b6'),
    (r'\bvit\s*\.?\s*b1\b', 'vitamin b1'),
    (r'\bfolicacid\b', 'folic acid'),
    (r'\briboflavine\b', 'riboflavin'),
    (r'\bthiamine\b', 'thiamin'),
    (r'\b(blinubis|blirbin|bilinubin)\b', 'bilirubin'),
    (r'\balenine\b', 'alanine'),
    (r'\baapertate\b', 'aspartate'),
    (r'\b(anisotraniferase|aminotransderase|aminotransfarase)\b', 'aminotransferase'),
    (r'\bganme[- ]?glstamyl\b', 'gamma-glutamyl'),
    (r'\bgamma[- ]?glstamyl\b', 'gamma-glutamyl'),
    (r'\bproteis\b', 'protein'),
    (r'\balbunin\b', 'albumin'),
    (r'\baig\s+retio\b', 'a/g ratio'),
    (r'\bdehydrogenese\b', 'dehydrogenase'),
    (r'\bmele\b', 'male'),
    (r'\bmsle\b', 'male'),
    (r'\bsenum\b', 'serum'),
    (r'\bbleod\b', 'blood'),
    (r'\buree\b', 'urea'),
    (r'\bnitregen\b', 'nitrogen'),
    (r'\bcreatiaine\b', 'creatinine'),
    (r'\bestineted\b', 'estimated'),
    (r'\bglceneralar\b', 'glomerular'),
    (r'\bpiltration\b', 'filtration'),
    (r'\brote\b', 'rate'),
    (r'\bsodiun\b', 'sodium'),
    (r'\bpotassism\b', 'potassium'),
    (r'\bbicarbotate\b', 'bicarbonate'),
    (r'\binerganic\b', 'inorganic'),
    (r'\bpaosphate\b', 'phosphate'),
    (r'\bmogaesium\b', 'magnesium'),
]


def normalize_text_for_alias_matching(text: str) -> str:
    """
    Normalizes input text for biomarker alias resolution:
    - Lowercases text
    - Applies regex-based OCR error cleanups
    - Replaces certain special characters with spaces
    - Collapses consecutive whitespace
    """
    if not text:
        return ""
    
    cleaned = text
    # Apply OCR mistake cleanups
    for pattern, replacement in OCR_CLEANUP_RULES:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    cleaned = cleaned.lower()
    # Normalize punctuation while preserving useful symbols for compound keys
    # Replace dots, commas, colons with space unless part of numbers
    cleaned = re.sub(r'[:;,\(\)\[\]]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


class AliasResolver:
    """
    100% Local-First deterministic biomarker alias resolver.
    Matches aliases prioritizing longest phrases first to prevent partial overlaps.
    Assigns alias_priority based on priority/standard/fallback aliases.
    """
    def __init__(self, aliases_path: str = DEFAULT_ALIASES_PATH, ref_path: str = DEFAULT_REF_PATH):
        self.aliases_path = aliases_path
        self.ref_path = ref_path
        self.canonical_to_aliases = self._load_aliases(aliases_path)
        self.priority_aliases_map, self.fallback_aliases_map = self._load_priority_metadata(ref_path)
        # Flattened list of (alias, canonical_key, priority_score), sorted descending by alias length
        self._sorted_aliases: List[Tuple[str, str, int]] = self._build_sorted_aliases()

    def _load_aliases(self, path: str) -> Dict[str, List[str]]:
        aliases_dict: Dict[str, List[str]] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                aliases_dict = json.load(f)
        
        # Merge from KFT registry
        try:
            from app.utils.kft_registry import KFT_BIOMARKERS
            for key, info in KFT_BIOMARKERS.items():
                if key not in aliases_dict:
                    aliases_dict[key] = []
                for alias in info.get("aliases", []):
                    if alias not in aliases_dict[key]:
                        aliases_dict[key].append(alias)
        except Exception:
            pass

        # Merge from LFT registry
        try:
            from app.utils.lft_registry import LFT_BIOMARKERS
            for key, info in LFT_BIOMARKERS.items():
                if key not in aliases_dict:
                    aliases_dict[key] = []
                for alias in info.get("aliases", []):
                    if alias not in aliases_dict[key]:
                        aliases_dict[key].append(alias)
        except Exception:
            pass

        return aliases_dict

    def _load_priority_metadata(self, path: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        priority_map: Dict[str, List[str]] = {}
        fallback_map: Dict[str, List[str]] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for bm in data.get("biomarkers", []):
                        key = bm.get("key")
                        if not key:
                            continue
                        if "priority_aliases" in bm:
                            priority_map[key] = [a.strip().lower() for a in bm["priority_aliases"]]
                        if "fallback_aliases" in bm:
                            fallback_map[key] = [a.strip().lower() for a in bm["fallback_aliases"]]
            except Exception:
                pass
        return priority_map, fallback_map

    def get_alias_priority(self, canonical_key: str, alias: str) -> int:
        norm_alias = alias.strip().lower()
        priorities = self.priority_aliases_map.get(canonical_key, [])
        fallbacks = self.fallback_aliases_map.get(canonical_key, [])

        if norm_alias in priorities:
            return 100
        if canonical_key == "vitamin_d3" or norm_alias in fallbacks and "d3" in norm_alias:
            return 50
        if canonical_key == "vitamin_d2" or norm_alias in fallbacks and "d2" in norm_alias:
            return 40
        if norm_alias in fallbacks:
            return 50
        # Default priority for standard aliases
        return 80

    def _build_sorted_aliases(self) -> List[Tuple[str, str, int]]:
        alias_list = []
        for canonical_key, aliases in self.canonical_to_aliases.items():
            for alias in aliases:
                norm_alias = alias.strip().lower()
                priority = self.get_alias_priority(canonical_key, norm_alias)
                alias_list.append((norm_alias, canonical_key, priority))
        # Sort by length descending, then alphabetically for deterministic order
        alias_list.sort(key=lambda x: (len(x[0]), x[0]), reverse=True)
        return alias_list

    def resolve(self, text: str, allowed_keys: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Resolves text to a canonical biomarker key.
        
        Args:
            text: Raw or pre-processed line string containing biomarker name.
            allowed_keys: Optional set/list of canonical keys to restrict search (e.g. for a specific category).

        Returns:
            Dict with canonical_key, matched_alias, alias_priority, match_confidence, or None if no match.
        """
        if not text:
            return None

        norm_line = normalize_text_for_alias_matching(text)
        if not norm_line:
            return None

        # Pass 1: Try direct match on line text (case-insensitive)
        for alias, canonical_key, priority in self._sorted_aliases:
            if allowed_keys is not None and canonical_key not in allowed_keys:
                continue

            if " " in alias or "/" in alias or "-" in alias or "%" in alias or "(" in alias:
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias) + r'(?![a-zA-Z0-9])'
            else:
                pattern = r'\b' + re.escape(alias) + r'\b'

            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return {
                    "canonical_key": canonical_key,
                    "matched_alias": alias,
                    "alias_priority": priority,
                    "matched_text": match.group(0),
                    "match_confidence": 1.0,
                    "span": match.span()
                }

        # Pass 2: Try match on normalized/cleaned line text
        for alias, canonical_key, priority in self._sorted_aliases:
            if allowed_keys is not None and canonical_key not in allowed_keys:
                continue

            if " " in alias or "/" in alias or "-" in alias or "%" in alias or "(" in alias:
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias) + r'(?![a-zA-Z0-9])'
            else:
                pattern = r'\b' + re.escape(alias) + r'\b'

            match = re.search(pattern, norm_line)
            if match:
                return {
                    "canonical_key": canonical_key,
                    "matched_alias": alias,
                    "alias_priority": priority,
                    "matched_text": match.group(0),
                    "match_confidence": 1.0,
                    "span": match.span()
                }

        return None


# Global singleton helper
_GLOBAL_RESOLVER = None


def get_alias_resolver(aliases_path: str = DEFAULT_ALIASES_PATH) -> AliasResolver:
    global _GLOBAL_RESOLVER
    if _GLOBAL_RESOLVER is None:
        _GLOBAL_RESOLVER = AliasResolver(aliases_path)
    return _GLOBAL_RESOLVER


def resolve_biomarker_alias(text: str, allowed_keys: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Deterministic helper function to resolve a biomarker alias from text.
    """
    resolver = get_alias_resolver()
    return resolver.resolve(text, allowed_keys=allowed_keys)
