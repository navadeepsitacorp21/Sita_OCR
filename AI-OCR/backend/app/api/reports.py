from fastapi import APIRouter

router = APIRouter(tags=["Reports"])

@router.get("/reports")
def list_reports():
    return []

@router.get("/reports/{report_id}")
def get_report(report_id: str):
    return {
        "report_id": report_id,
        "status": "coming soon"
    }