import requests
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
img_path = r"backend/tests/fixtures/ocr/original_aster_cbc.png"

with open(img_path, 'rb') as f:
    resp = requests.post("http://127.0.0.1:8000/api/v1/upload", files={"file": ("original_aster_cbc.png", f, "image/png")})

print("HTTP Status Code:", resp.status_code)
data = resp.json()
parsed = data.get("parsed_report", {})
summary = data.get("health_summary", {})
vault_info = data.get("health_vault", {})

print("\n--- API RESPONSE SUMMARY ---")
print("Report Type:", parsed.get("report_type"))
print("Parser Version:", parsed.get("parser_version"))
print("Biomarkers Found:", parsed.get("biomarkers_found"))
print("Overall Status:", summary.get("overall_status"))
print("Normal Count:", summary.get("normal_biomarkers"))
print("High Count:", summary.get("high_biomarkers"))
print("Low Count:", summary.get("low_biomarkers"))
print("Abnormal Count:", summary.get("abnormal_count"))

print("\n--- 15/15 BIOMARKERS EXTRACTED ---")
for idx, b in enumerate(parsed.get("biomarkers", []), 1):
    ref_safe = str(b.get("reference_range", "")).encode("ascii", "replace").decode("ascii")
    print(f"{idx:02d}. {b.get('name'):<32} | Value: {b.get('value')} {b.get('unit'):<10} | Status: {b.get('status'):<7} | Ref: {ref_safe} (src={b.get('reference_source')})")

print("\n--- TESTING HEALTH VAULT ---")
rid = vault_info.get("report_id")
print("Saved Report ID:", rid)
if rid:
    detail = requests.get(f"http://127.0.0.1:8000/api/v1/health-vault/reports/{rid}").json()
    rep = detail.get("report", {})
    p = rep.get("parsed_report", {})
    s = rep.get("health_summary", {})
    print(f"Vault Report Type: {p.get('report_type')}")
    print(f"Vault Parser Version: {p.get('parser_version')}")
    print(f"Vault Biomarkers Found: {p.get('biomarkers_found')}")
    print(f"Vault Overall Status: {s.get('overall_status')}")
    print(f"Vault Normal Count: {s.get('normal_biomarkers')}")
    print(f"Vault Low Count: {s.get('low_biomarkers')}")
