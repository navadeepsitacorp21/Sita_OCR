from typing import Dict, List, Optional, Any

LFT_BIOMARKERS: Dict[str, Dict[str, Any]] = {
    "total_bilirubin": {
        "key": "total_bilirubin",
        "name": "Total Bilirubin",
        "display_name": "Total Bilirubin",
        "aliases": [
            "total bilirubin",
            "serum bilirubin total",
            "bilirubin total",
            "total serum bilirubin",
            "bilirubin (total)",
            "bilirubin - total",
            "bilirubin"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "0.2-1.2",
        "validation_range": (0.0, 25.0),
        "group": "bilirubin"
    },
    "direct_bilirubin": {
        "key": "direct_bilirubin",
        "name": "Direct Bilirubin",
        "display_name": "Direct Bilirubin",
        "aliases": [
            "direct bilirubin",
            "conjugated bilirubin",
            "serum bilirubin direct",
            "bilirubin direct",
            "bilirubin (direct)",
            "bilirubin - direct"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "0.0-0.3",
        "validation_range": (0.0, 10.0),
        "group": "bilirubin"
    },
    "indirect_bilirubin": {
        "key": "indirect_bilirubin",
        "name": "Indirect Bilirubin",
        "display_name": "Indirect Bilirubin",
        "aliases": [
            "indirect bilirubin",
            "unconjugated bilirubin",
            "serum bilirubin indirect",
            "bilirubin indirect",
            "bilirubin (indirect)",
            "bilirubin - indirect"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "0.2-0.9",
        "validation_range": (0.0, 20.0),
        "group": "bilirubin"
    },
    "alt_sgpt": {
        "key": "alt_sgpt",
        "name": "ALT (SGPT)",
        "display_name": "ALT (SGPT)",
        "aliases": [
            "alanine aminotransferase",
            "alanine transaminase",
            "serum glutamic pyruvic transaminase",
            "alt (sgpt)",
            "sgpt / alt",
            "alt / sgpt",
            "sgpt",
            "alt"
        ],
        "default_unit": "U/L",
        "default_reference_range": "7-56",
        "validation_range": (0.0, 1000.0),
        "group": "liver_enzymes"
    },
    "ast_sgot": {
        "key": "ast_sgot",
        "name": "AST (SGOT)",
        "display_name": "AST (SGOT)",
        "aliases": [
            "aspartate aminotransferase",
            "aspartate transaminase",
            "serum glutamic oxaloacetic transaminase",
            "ast (sgot)",
            "sgot / ast",
            "ast / sgot",
            "sgot",
            "ast"
        ],
        "default_unit": "U/L",
        "default_reference_range": "8-40",
        "validation_range": (0.0, 1000.0),
        "group": "liver_enzymes"
    },
    "alkaline_phosphatase": {
        "key": "alkaline_phosphatase",
        "name": "Alkaline Phosphatase",
        "display_name": "Alkaline Phosphatase",
        "aliases": [
            "serum alkaline phosphatase",
            "alkaline phosphatase (alp)",
            "alkaline phosphatase",
            "alk phos",
            "alp"
        ],
        "default_unit": "U/L",
        "default_reference_range": "44-147",
        "validation_range": (20.0, 1500.0),
        "group": "liver_enzymes"
    },
    "ggt": {
        "key": "ggt",
        "name": "Gamma GT (GGT)",
        "display_name": "Gamma GT (GGT)",
        "aliases": [
            "gamma-glutamyl transferase",
            "gamma glutamyl transferase",
            "gamma glutamyl transpeptidase",
            "gamma-gt (ggt)",
            "gamma gt (ggt)",
            "gamma-gt",
            "gamma gt",
            "ggt",
            "ggtp"
        ],
        "default_unit": "U/L",
        "default_reference_range": "10-49",
        "validation_range": (5.0, 500.0),
        "group": "liver_enzymes"
    },
    "total_protein": {
        "key": "total_protein",
        "name": "Total Protein",
        "display_name": "Total Protein",
        "aliases": [
            "serum total protein",
            "protein (total)",
            "protein total",
            "total proteins",
            "total protein",
            "serum protein"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "6.0-8.3",
        "validation_range": (2.0, 12.0),
        "group": "proteins"
    },
    "albumin": {
        "key": "albumin",
        "name": "Albumin",
        "display_name": "Albumin",
        "aliases": [
            "albumin - serum",
            "serum albumin",
            "albumin"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "3.5-5.0",
        "validation_range": (1.0, 8.0),
        "group": "proteins"
    },
    "globulin": {
        "key": "globulin",
        "name": "Globulin",
        "display_name": "Globulin",
        "aliases": [
            "globulin - serum",
            "serum globulin",
            "globulin"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "2.0-3.5",
        "validation_range": (0.5, 8.0),
        "group": "proteins"
    },
    "albumin_globulin_ratio": {
        "key": "albumin_globulin_ratio",
        "name": "Albumin / Globulin Ratio",
        "display_name": "A/G Ratio",
        "aliases": [
            "albumin / globulin ratio",
            "albumin/globulin ratio",
            "albumin globulin ratio",
            "a/g ratio",
            "a / g ratio",
            "a:g ratio",
            "ag ratio"
        ],
        "default_unit": "ratio",
        "default_reference_range": "1.0-2.1",
        "validation_range": (0.5, 3.5),
        "group": "ratios"
    },
    "ldh": {
        "key": "ldh",
        "name": "Lactate Dehydrogenase (LDH)",
        "display_name": "LDH",
        "aliases": [
            "lactate dehydrogenase",
            "lactate dehydrogenase (ldh)",
            "serum ldh",
            "ldh"
        ],
        "default_unit": "U/L",
        "default_reference_range": "140-280",
        "validation_range": (50.0, 1500.0),
        "group": "liver_enzymes"
    }
}


def get_lft_biomarker_info(key: str) -> Optional[Dict[str, Any]]:
    return LFT_BIOMARKERS.get(key)
