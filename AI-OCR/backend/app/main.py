from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health_check import router as health_router
from app.api.upload import router as upload_router
from app.api.reports import router as reports_router
from app.api.health_vault import router as health_vault_router

app = FastAPI(
    title="SITA OCR Engine",
    version="1.0.0",
    description="Standalone OCR and Health Vault service for SITA"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(health_vault_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "service": "SITA OCR Engine",
        "status": "running",
        "version": "1.3.2"
    }