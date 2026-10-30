import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.utils.alias_resolver import resolve_biomarker_alias
from app.utils.cbc_registry import CBC_BIOMARKERS

tokens = [
    "Mean Platelet Volume, MPV",
    "R.D.W. -CV",
    "R.D.W. -SD",
    "Hemoglobin",
    "Total Leukocyte Count",
    "Total RBC Count",
    "Hematocrit Value, Hct",
    "Mean CorpuscularVolume, MCV",
    "Mean Cell Haemoglobin, MCH",
    "Mean Cell Haemoglobin CON,",
    "MCHC",
    "Total Platelet Count"
]

cat_allowed_keys = list(CBC_BIOMARKERS.keys())

for t in tokens:
    res = resolve_biomarker_alias(t, allowed_keys=cat_allowed_keys)
    if res:
        print(f"MATCH: '{t}' -> {res['canonical_key']} (alias: '{res['matched_alias']}')")
    else:
        print(f"NO MATCH: '{t}'")
