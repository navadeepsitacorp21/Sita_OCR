from typing import Dict, List, Optional, Any

LIPID_BIOMARKERS: Dict[str, Dict[str, Any]] = {
    "total_cholesterol": {
        "key": "total_cholesterol",
        "name": "Total Cholesterol",
        "display_name": "Total Cholesterol",
        "aliases": [
            "total cholesterol",
            "serum cholesterol",
            "cholesterol",
            "cholesterol total",
            "s. cholesterol",
            "s cholesterol",
            "tot cholesterol",
            "total cholesterin"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "<200",
        "validation_range": (50.0, 1000.0),
        "group": "cholesterol"
    },
    "triglycerides": {
        "key": "triglycerides",
        "name": "Triglycerides",
        "display_name": "Triglycerides",
        "aliases": [
            "triglycerides",
            "serum triglycerides",
            "triglyceride",
            "s. triglycerides",
            "s triglycerides",
            "tg",
            "s.tg"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "<150",
        "validation_range": (10.0, 2500.0),
        "group": "triglycerides"
    },
    "hdl": {
        "key": "hdl",
        "name": "HDL Cholesterol",
        "display_name": "HDL Cholesterol",
        "aliases": [
            "hdl cholesterol",
            "hdl-c",
            "high density lipoprotein",
            "hdl - cholesterol",
            "hdl",
            "hdl direct",
            "direct hdl",
            "s. hdl",
            "hdl-cholesterol"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": ">40",
        "validation_range": (5.0, 200.0),
        "group": "cholesterol"
    },
    "ldl": {
        "key": "ldl",
        "name": "LDL Cholesterol",
        "display_name": "LDL Cholesterol",
        "aliases": [
            "ldl cholesterol",
            "ldl-c",
            "low density lipoprotein",
            "ldl - cholesterol",
            "ldl",
            "ldl cholesterol (calculated)",
            "ldl cholesterol calculated",
            "ldl direct",
            "direct ldl",
            "s. ldl",
            "ldl-cholesterol"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "<100",
        "validation_range": (10.0, 600.0),
        "group": "cholesterol"
    },
    "vldl": {
        "key": "vldl",
        "name": "VLDL Cholesterol",
        "display_name": "VLDL Cholesterol",
        "aliases": [
            "vldl cholesterol",
            "vldl-c",
            "very low density lipoprotein",
            "vldl - cholesterol",
            "vldl",
            "vldl cholesterol (calculated)",
            "vldl cholesterol calculated",
            "s. vldl",
            "vldl-cholesterol"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "5-40",
        "validation_range": (1.0, 300.0),
        "group": "cholesterol"
    },
    "non_hdl": {
        "key": "non_hdl",
        "name": "Non-HDL Cholesterol",
        "display_name": "Non-HDL Cholesterol",
        "aliases": [
            "non-hdl cholesterol",
            "non hdl cholesterol",
            "non-hdl-c",
            "non-hdl",
            "non hdl",
            "non-hdl-cholesterol",
            "non hdl-c"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "<130",
        "validation_range": (20.0, 900.0),
        "group": "cholesterol"
    },
    "cholesterol_hdl_ratio": {
        "key": "cholesterol_hdl_ratio",
        "name": "Cholesterol / HDL Ratio",
        "display_name": "Cholesterol / HDL Ratio",
        "aliases": [
            "total cholesterol / hdl ratio",
            "total cholesterol/hdl ratio",
            "cholesterol/hdl ratio",
            "tc/hdl ratio",
            "tc / hdl ratio",
            "chol/hdl ratio",
            "cholesterol / hdl ratio",
            "tc / hdl",
            "tc/hdl",
            "chol / hdl",
            "chol/hdl"
        ],
        "default_unit": "ratio",
        "default_reference_range": "3-5",
        "validation_range": (0.5, 30.0),
        "group": "ratios"
    },
    "ldl_hdl_ratio": {
        "key": "ldl_hdl_ratio",
        "name": "LDL / HDL Ratio",
        "display_name": "LDL / HDL Ratio",
        "aliases": [
            "ldl / hdl ratio",
            "ldl/hdl ratio",
            "ldl to hdl ratio",
            "ldl:hdl ratio",
            "ldl / hdl",
            "ldl/hdl",
            "ldl-c / hdl-c ratio",
            "ldl-c/hdl-c ratio",
            "ldl-c / hdl-c",
            "ldl-c/hdl-c"
        ],
        "default_unit": "ratio",
        "default_reference_range": "<3.0",
        "validation_range": (0.1, 20.0),
        "group": "ratios",
        "optional": True
    },
    "apolipoprotein_a1": {
        "key": "apolipoprotein_a1",
        "name": "Apolipoprotein A1 (ApoA1)",
        "display_name": "Apolipoprotein A1 (ApoA1)",
        "aliases": [
            "apolipoprotein a1 (apoa1)",
            "apolipoprotein a1",
            "apolipoprotein a-1",
            "apolipoprotein-a1",
            "apo a1",
            "apoa1",
            "apo-a1",
            "apo a-1",
            "apolipoprotein a"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "110-205",
        "validation_range": (10.0, 400.0),
        "group": "apolipoproteins",
        "optional": True
    },
    "apolipoprotein_b": {
        "key": "apolipoprotein_b",
        "name": "Apolipoprotein B (ApoB)",
        "display_name": "Apolipoprotein B (ApoB)",
        "aliases": [
            "apolipoprotein b (apob)",
            "apolipoprotein b",
            "apolipoprotein-b",
            "apo b",
            "apob",
            "apo-b",
            "apolipoprotein-b (apob)"
        ],
        "default_unit": "mg/dL",
        "default_reference_range": "60-130",
        "validation_range": (10.0, 350.0),
        "group": "apolipoproteins",
        "optional": True
    },
    "apob_apoa1_ratio": {
        "key": "apob_apoa1_ratio",
        "name": "Apo B / Apo A1 Ratio",
        "display_name": "Apo B / Apo A1 Ratio",
        "aliases": [
            "apo b / apo a1 ratio",
            "apob / apoa1 ratio",
            "apo b/apo a1 ratio",
            "apob/apoa1 ratio",
            "apo b / apo a1",
            "apob / apoa1",
            "apo b/apo a1",
            "apob/apoa1",
            "apo b:apo a1 ratio",
            "apob:apoa1 ratio"
        ],
        "default_unit": "ratio",
        "default_reference_range": "0.35-1.0",
        "validation_range": (0.05, 10.0),
        "group": "ratios",
        "optional": True
    }
}

