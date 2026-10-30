from typing import Dict, List, Optional, Any

CBC_ALIASES = {
    "total leukocyte count": "wbc_count",
    "total leucocyte count": "wbc_count",
    "white blood cell count": "wbc_count",
    "tlc": "wbc_count",
    "wbc": "wbc_count",
    "total rbc count": "rbc_count",
    "red blood cell count": "rbc_count",
    "total rbc": "rbc_count",
    "rbc": "rbc_count",
    "haematocrit": "pcv",
    "hematocrit": "pcv",
    "hct": "pcv",
    "pcv": "pcv",
    "packed cell volume": "pcv",
    "mean platelet volume": "mpv",
    "mpv": "mpv",
    "rdw cv": "rdw_cv",
    "rdw-cv": "rdw_cv",
    "rdw sd": "rdw_sd",
    "rdw-sd": "rdw_sd",
    "mean cell haemoglobin conc": "mchc",
    "mean cell hemoglobin conc": "mchc",
    "mean corpuscular hemoglobin concentration": "mchc",
    "mchc": "mchc",
    "total platelet count": "platelet_count",
    "platelet count": "platelet_count",
    "platelets": "platelet_count",
    "plt": "platelet_count",
    "hemoglobin": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "mcv": "mcv",
    "mch": "mch",
    "neutrophils": "neutrophils",
    "lymphocytes": "lymphocytes",
    "monocytes": "monocytes",
    "eosinophils": "eosinophils",
    "basophils": "basophils"
}

CBC_CANONICAL_NAMES = {
    "hemoglobin": "Hemoglobin",
    "rbc_count": "RBC Count",
    "wbc_count": "WBC Count",
    "platelet_count": "Platelet Count",
    "pcv": "Hematocrit",
    "mcv": "MCV",
    "mch": "MCH",
    "mchc": "MCHC",
    "mpv": "MPV",
    "rdw": "RDW",
    "rdw_cv": "RDW-CV",
    "rdw_sd": "RDW-SD",
    "neutrophils": "Neutrophils",
    "lymphocytes": "Lymphocytes",
    "monocytes": "Monocytes",
    "eosinophils": "Eosinophils",
    "basophils": "Basophils"
}


def resolve_cbc_alias(alias: str) -> Optional[str]:
    """
    Resolve a given CBC alias string to its canonical key.
    """
    if not alias:
        return None
    cleaned = alias.lower().strip()
    return CBC_ALIASES.get(cleaned)


def get_cbc_canonical_name(key: str) -> str:
    """
    Get human-readable display name for CBC canonical key.
    """
    return CBC_CANONICAL_NAMES.get(key, key.upper())
