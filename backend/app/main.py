import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health_check import router as health_router
from app.api.upload import router as upload_router
from app.api.reports import router as reports_router
from app.api.health_vault import router as health_vault_router
from app.api.medical_reports import router as medical_reports_router
from app.api.ocr import router as ocr_router

app = FastAPI(
    title="SITA OCR Engine",
    version="1.0.0",
    description="Standalone OCR and Health Vault service for SITA"
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In production, set ALLOWED_ORIGINS env var to a comma-separated list of
# allowed frontend URLs, e.g. "https://sita-frontend.onrender.com".
# Defaults to localhost development origins only.
# NOTE: allow_credentials=True requires explicit origins — "*" is forbidden by browsers.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if _raw_origins.strip():
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    _allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(health_vault_router, prefix="/api/v1")
app.include_router(medical_reports_router, prefix="/api/v1")
app.include_router(ocr_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "service": "SITA OCR Engine",
        "status": "running",
        "version": "1.3.2"
    }