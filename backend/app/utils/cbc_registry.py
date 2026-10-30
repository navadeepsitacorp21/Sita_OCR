from typing import Dict, List, Optional, Any

CBC_BIOMARKERS: Dict[str, Dict[str, Any]] = {
    "rbc_count": {
        "key": "rbc_count",
        "name": "RBC Count",
        "display_name": "RBC Count",
        "aliases": [
            "total rbc count",
            "red blood cell count",
            "total rbc",
            "red blood cells",
            "erythrocyte count",
            "erythrocytes",
            "rbc count",
            "rbc"
        ],
        "default_unit": "10^6/uL",
        "default_reference_range": "4.0-5.5",
        "validation_range": (1.0, 10.0),
        "group": "rbc_indices"
    },
    "hemoglobin": {
        "key": "hemoglobin",
        "name": "Hemoglobin",
        "display_name": "Hemoglobin",
        "aliases": [
            "haemoglobin (hb)",
            "hemoglobin (hb)",
            "haemoglobin",
            "hemoglobin",
            "hb",
            "hgb"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "12.0-17.0",
        "validation_range": (3.0, 25.0),
        "group": "rbc_indices"
    },
    "pcv": {
        "key": "pcv",
        "name": "Hematocrit",
        "display_name": "Hematocrit / PCV",
        "aliases": [
            "packed cell volume (pcv)",
            "packed cell volume",
            "hematocrit value, hct",
            "hematocrit value",
            "haematocrit",
            "hematocrit",
            "pcv",
            "hct"
        ],
        "default_unit": "%",
        "default_reference_range": "36-50",
        "validation_range": (10.0, 75.0),
        "group": "rbc_indices"
    },
    "mcv": {
        "key": "mcv",
        "name": "MCV",
        "display_name": "MCV",
        "aliases": [
            "mean corpuscular volume, mcv",
            "mean corpuscularvolume, mcv",
            "mean corpuscularvolume",
            "mean corpuscular volume",
            "mean cell volume",
            "mcv"
        ],
        "default_unit": "fL",
        "default_reference_range": "80-101",
        "validation_range": (40.0, 150.0),
        "group": "rbc_indices"
    },
    "mch": {
        "key": "mch",
        "name": "MCH",
        "display_name": "MCH",
        "aliases": [
            "mean cell haemoglobin, mch",
            "mean cell hemoglobin, mch",
            "mean cell haemoglobin",
            "mean cell hemoglobin",
            "mean corpuscular hemoglobin",
            "mean corpuscular haemoglobin",
            "mch"
        ],
        "default_unit": "pg",
        "default_reference_range": "27-32",
        "validation_range": (10.0, 50.0),
        "group": "rbc_indices"
    },
    "mchc": {
        "key": "mchc",
        "name": "MCHC",
        "display_name": "MCHC",
        "aliases": [
            "mean cell haemoglobin concentration",
            "mean cell hemoglobin concentration",
            "mean cell haemoglobin conc",
            "mean cell hemoglobin conc",
            "mean cell haemoglobin con",
            "mean cell hemoglobin con",
            "mean corpuscular hemoglobin concentration",
            "mean corpuscular haemoglobin concentration",
            "mchc"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "31.5-34.5",
        "validation_range": (20.0, 45.0),
        "group": "rbc_indices"
    },
    "rdw": {
        "key": "rdw",
        "name": "RDW",
        "display_name": "RDW",
        "aliases": [
            "red cell distribution width",
            "rdw"
        ],
        "default_unit": "%",
        "default_reference_range": "11.5-14.5",
        "validation_range": (5.0, 35.0),
        "group": "rbc_indices"
    },
    "wbc_count": {
        "key": "wbc_count",
        "name": "WBC Count",
        "display_name": "Total WBC Count",
        "aliases": [
            "total wbc count",
            "total leukocyte count",
            "total leucocyte count",
            "white blood cell count",
            "total wbc",
            "leucocytes",
            "leukocytes",
            "tlc",
            "wbc count",
            "wbc"
        ],
        "default_unit": "10^3/uL",
        "default_reference_range": "4.0-11.0",
        "validation_range": (0.5, 100.0),
        "group": "wbc_indices"
    },
    "neutrophils": {
        "key": "neutrophils",
        "name": "Neutrophils",
        "display_name": "Neutrophils",
        "aliases": [
            "segmented neutrophils",
            "neutrophil %",
            "neutrophils",
            "neutrophil",
            "polymorphs",
            "neut %",
            "neut",
            "pmn"
        ],
        "default_unit": "%",
        "default_reference_range": "40-80",
        "validation_range": (0.0, 100.0),
        "group": "differential_wbc"
    },
    "lymphocytes": {
        "key": "lymphocytes",
        "name": "Lymphocytes",
        "display_name": "Lymphocytes",
        "aliases": [
            "lywphocytes",
            "lywphocyte",
            "lymphocyte %",
            "lymphocytes",
            "lymphocyte",
            "lymph %",
            "lymphs",
            "lymph"
        ],
        "default_unit": "%",
        "default_reference_range": "20-40",
        "validation_range": (0.0, 100.0),
        "group": "differential_wbc"
    },
    "eosinophils": {
        "key": "eosinophils",
        "name": "Eosinophils",
        "display_name": "Eosinophils",
        "aliases": [
            "eosinophitls",
            "eosinophits",
            "eosinophil %",
            "eosinophils",
            "eosinophil",
            "eos %",
            "eos"
        ],
        "default_unit": "%",
        "default_reference_range": "1-6",
        "validation_range": (0.0, 100.0),
        "group": "differential_wbc"
    },
    "monocytes": {
        "key": "monocytes",
        "name": "Monocytes",
        "display_name": "Monocytes",
        "aliases": [
            "manacytes",
            "manacyte",
            "monocyte %",
            "monocytes",
            "monocyte",
            "mono %",
            "monos",
            "mono"
        ],
        "default_unit": "%",
        "default_reference_range": "2-8",
        "validation_range": (0.0, 100.0),
        "group": "differential_wbc"
    },
    "basophils": {
        "key": "basophils",
        "name": "Basophils",
        "display_name": "Basophils",
        "aliases": [
            "basophil %",
            "basophils",
            "basophil",
            "baso %",
            "baso"
        ],
        "default_unit": "%",
        "default_reference_range": "0-2",
        "validation_range": (0.0, 100.0),
        "group": "differential_wbc"
    },
    "platelet_count": {
        "key": "platelet_count",
        "name": "Platelet Count",
        "display_name": "Platelet Count",
        "aliases": [
            "total platelet count",
            "plate let count",
            "platelet count",
            "thrombocyte count",
            "thrombocytes",
            "plateles",
            "platelets",
            "platelet",
            "plt"
        ],
        "default_unit": "10^3/uL",
        "default_reference_range": "150-450",
        "validation_range": (5.0, 2000.0),
        "group": "platelet_indices"
    },
    "mpv": {
        "key": "mpv",
        "name": "MPV",
        "display_name": "Mean Platelet Volume (MPV)",
        "aliases": [
            "mean platelet volume, mpv",
            "mean platelet volume",
            "mpv"
        ],
        "default_unit": "fL",
        "default_reference_range": "7.5-11.5",
        "validation_range": (3.0, 30.0),
        "group": "platelet_indices"
    },
    "rdw_cv": {
        "key": "rdw_cv",
        "name": "RDW-CV",
        "display_name": "RDW-CV",
        "aliases": [
            "red cell distribution width - cv",
            "r.d.w. - cv",
            "r.d.w. -cv",
            "r.d.w. cv",
            "rdw - cv",
            "rdw-cv",
            "rdw cv"
        ],
        "default_unit": "%",
        "default_reference_range": "11.5-14.5",
        "validation_range": (5.0, 35.0),
        "group": "rbc_indices",
        "optional": True
    },
    "rdw_sd": {
        "key": "rdw_sd",
        "name": "RDW-SD",
        "display_name": "RDW-SD",
        "aliases": [
            "red cell distribution width - sd",
            "r.d.w. - sd",
            "r.d.w. -sd",
            "r.d.w. sd",
            "rdw - sd",
            "rdw-sd",
            "rdw sd"
        ],
        "default_unit": "fL",
        "default_reference_range": "39-46",
        "validation_range": (15.0, 80.0),
        "group": "rbc_indices",
        "optional": True
    }
}

CBC_ALIASES = {
    alias.lower(): key
    for key, data in CBC_BIOMARKERS.items()
    for alias in data.get("aliases", [])
}

CBC_CANONICAL_NAMES = {
    key: data.get("display_name", data.get("name", key.upper()))
    for key, data in CBC_BIOMARKERS.items()
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
