from typing import Dict, List, Optional, Any

KFT_BIOMARKERS: Dict[str, Dict[str, Any]] = {
    "serum_urea": {
        "key": "serum_urea",
        "name": "Serum Urea",
        "display_name": "Serum Urea",
        "aliases": [
            "serum urea",
            "urea",
            "senum urea",
            "blood urea",
            "s. urea",
            "s urea",
            "urea - serum",
            "urea serum"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "15-40",
        "validation_range": (1.0, 300.0),
        "group": "kidney_function"
    },
    "bun": {
        "key": "bun",
        "name": "Blood Urea Nitrogen (BUN)",
        "display_name": "Blood Urea Nitrogen (BUN)",
        "aliases": [
            "blood urea nitrogen (bun)",
            "blood urea nitrogen",
            "bleod uree nitregen (bun)",
            "bleod uree nitregen",
            "uree nitregen",
            "bun",
            "serum bun",
            "urea nitrogen",
            "b.u.n."
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "7-20",
        "validation_range": (1.0, 150.0),
        "group": "kidney_function"
    },
    "serum_creatinine": {
        "key": "serum_creatinine",
        "name": "Serum Creatinine",
        "display_name": "Serum Creatinine",
        "aliases": [
            "serum creatinine",
            "creatinine",
            "senum creatiaine",
            "creatiaine",
            "s. creatinine",
            "s creatinine",
            "sr creatinine",
            "creatinine - serum"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "0.6-1.3",
        "validation_range": (0.1, 30.0),
        "group": "kidney_function"
    },
    "egfr": {
        "key": "egfr",
        "name": "Estimated Glomerular Filtration Rate (eGFR)",
        "display_name": "Estimated Glomerular Filtration Rate (eGFR)",
        "aliases": [
            "estimated glomerular filtration rate (egfr)",
            "estimated glomerular filtration rate",
            "estineted glceneralar piltration rote (egfr)",
            "estineted glceneralar piltration rote",
            "egfr",
            "e-gfr",
            "estimated gfr",
            "gfr (estimated)",
            "egfr (ckd-epi)",
            "glomerular filtration rate",
            "egfr category"
        ],
        "default_unit": "mL/min/1.73m²",
        "default_reference_range": ">=90",
        "validation_range": (5.0, 250.0),
        "group": "kidney_filtration"
    },
    "uric_acid": {
        "key": "uric_acid",
        "name": "Serum Uric Acid",
        "display_name": "Serum Uric Acid",
        "aliases": [
            "serum uric acid",
            "uric acid",
            "senum uric acid",
            "s. uric acid",
            "s uric acid",
            "uric acid - serum",
            "urate"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "2.6-7.2",
        "validation_range": (0.5, 25.0),
        "group": "metabolic_markers"
    },
    "sodium": {
        "key": "sodium",
        "name": "Serum Sodium",
        "display_name": "Serum Sodium",
        "aliases": [
            "serum sodium",
            "sodium",
            "senum sodiun",
            "sodiun",
            "sodium (na+)",
            "sodium - serum",
            "s. sodium",
            "s sodium",
            "na+"
        ],
        "default_unit": "mmol/L",
        "default_reference_range": "135-145",
        "validation_range": (50.0, 200.0),
        "group": "electrolytes"
    },
    "potassium": {
        "key": "potassium",
        "name": "Serum Potassium",
        "display_name": "Serum Potassium",
        "aliases": [
            "serum potassium",
            "potassium",
            "serum potassism",
            "potassism",
            "potassium (k+)",
            "potassium - serum",
            "s. potassium",
            "s potassium",
            "k+"
        ],
        "default_unit": "mmol/L",
        "default_reference_range": "3.5-5.0",
        "validation_range": (1.0, 10.0),
        "group": "electrolytes"
    },
    "chloride": {
        "key": "chloride",
        "name": "Serum Chloride",
        "display_name": "Serum Chloride",
        "aliases": [
            "serum chloride",
            "chloride",
            "senum chloride",
            "s. chloride",
            "s chloride",
            "chloride - serum",
            "cl-",
            "cl"
        ],
        "default_unit": "mmol/L",
        "default_reference_range": "98-107",
        "validation_range": (50.0, 180.0),
        "group": "electrolytes"
    },
    "bicarbonate": {
        "key": "bicarbonate",
        "name": "Serum Bicarbonate (CO₂, Total)",
        "display_name": "Serum Bicarbonate (CO₂, Total)",
        "aliases": [
            "serum bicarbonate (co; total)",
            "serum bicarbonate (co2 total)",
            "serum bicarbonate (co2, total)",
            "serum bicarbotate (co; total)",
            "serum bicarbotate",
            "bicarbotate",
            "serum bicarbonate",
            "bicarbonate",
            "co2 total",
            "total co2",
            "co2",
            "carbon dioxide",
            "total carbon dioxide",
            "serum co2"
        ],
        "default_unit": "mmol/L",
        "default_reference_range": "22-29",
        "validation_range": (5.0, 60.0),
        "group": "electrolytes"
    },
    "calcium": {
        "key": "calcium",
        "name": "Serum Calcium",
        "display_name": "Serum Calcium",
        "aliases": [
            "serum calcium",
            "calcium, total",
            "calcium total",
            "total calcium",
            "calcium",
            "s. calcium",
            "s calcium",
            "calcium - serum",
            "ca++"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "8.5-10.5",
        "validation_range": (2.0, 20.0),
        "group": "minerals"
    },
    "phosphorus": {
        "key": "phosphorus",
        "name": "Serum Phosphorus (Inorganic Phosphate)",
        "display_name": "Serum Phosphorus (Inorganic Phosphate)",
        "aliases": [
            "serum phosphorus (inerganic paosphate)",
            "serum phosphorus (inorganic phosphate)",
            "serum phosphorus",
            "phosphorus",
            "inorganic phosphate",
            "phosphate",
            "serum phosphate",
            "s. phosphorus",
            "s phosphorus",
            "inerganic paosphate",
            "phosphorus - serum"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "2.5-4.5",
        "validation_range": (0.5, 15.0),
        "group": "minerals"
    },
    "magnesium": {
        "key": "magnesium",
        "name": "Serum Magnesium",
        "display_name": "Serum Magnesium",
        "aliases": [
            "serum magnesium",
            "magnesium",
            "serum mogaesium",
            "mogaesium",
            "s. magnesium",
            "s magnesium",
            "magnesium - serum",
            "mg++",
            "mg"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "1.7-2.4",
        "validation_range": (0.5, 10.0),
        "group": "minerals"
    },
    "alkaline_phosphatase": {
        "key": "alkaline_phosphatase",
        "name": "Alkaline Phosphatase (ALP)",
        "display_name": "Alkaline Phosphatase (ALP)",
        "aliases": [
            "alkaline phosphatase (alp)",
            "alkaline phosphatase",
            "serum alkaline phosphatase",
            "alk phos",
            "alp"
        ],
        "default_unit": "U/L",
        "default_reference_range": "30-120",
        "validation_range": (20.0, 1500.0),
        "group": "enzymes",
        "optional": True
    },
    "total_protein": {
        "key": "total_protein",
        "name": "Total Protein",
        "display_name": "Total Protein",
        "aliases": [
            "total protein",
            "serum total protein",
            "protein total",
            "protein (total)",
            "total proteins",
            "serum protein"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "5.7-8.2",
        "validation_range": (2.0, 12.0),
        "group": "proteins",
        "optional": True
    },
    "albumin": {
        "key": "albumin",
        "name": "Albumin",
        "display_name": "Albumin",
        "aliases": [
            "albumin",
            "serum albumin",
            "albumin - serum"
        ],
        "default_unit": "g/dL",
        "default_reference_range": "3.2-4.8",
        "validation_range": (1.0, 8.0),
        "group": "proteins",
        "optional": True
    },
    "urea_creatinine_ratio": {
        "key": "urea_creatinine_ratio",
        "name": "Urea / Creatinine Ratio",
        "display_name": "Urea / Creatinine Ratio",
        "aliases": [
            "urea / creatinine ratio",
            "urea/creatinine ratio",
            "bun/creatinine ratio",
            "bun / creatinine ratio",
            "urea : creatinine ratio",
            "bun:creatinine ratio"
        ],
        "default_unit": "ratio",
        "default_reference_range": "10-20",
        "validation_range": (1.0, 100.0),
        "group": "ratios",
        "optional": True
    }
}
