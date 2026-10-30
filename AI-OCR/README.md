# AI-OCR Engine & Health Vault

AI-powered OCR system for automated processing, classification, extraction, and summarization of medical lab reports.

## Project Structure

```
AI-OCR/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload.py            # Report upload API route
│   │   │   ├── reports.py           # Fetch & manage reports API route
│   │   │   └── health_check.py      # Health status endpoint
│   │   │
│   │   ├── services/
│   │   │   ├── ocr_service.py       # Core OCR integration service
│   │   │   ├── classifier_service.py# Report classifier
│   │   │   ├── parser_service.py    # Structured biomarker parser
│   │   │   ├── summary_service.py   # Clinical insight summarizer
│   │   │   └── storage_service.py   # Storage & workflow orchestration
│   │   │
│   │   ├── models/
│   │   │   ├── report_models.py     # Report schemas & models
│   │   │   └── biomarker_models.py  # Biomarker data schemas
│   │   │
│   │   ├── utils/
│   │   │   ├── pdf_utils.py         # PDF conversion utilities
│   │   │   ├── image_utils.py       # Image preprocessing
│   │   │   └── text_utils.py        # Text cleaning & regex utilities
│   │   │
│   │   └── main.py                  # FastAPI application entrypoint
│   │
│   ├── data/
│   │   ├── biomarker_reference.json # Reference ranges for biomarkers
│   │   ├── report_patterns.json     # Regex & pattern matching templates
│   │   └── sample_outputs/          # Extracted result cache/samples
│   │
│   ├── tests/                       # Automated backend tests
│   ├── requirements.txt             # Python dependencies
│   └── .env                         # Environment configuration
│
├── frontend/                        # Web app UI
├── docs/                            # Project documentation
├── sample_reports/                  # Test PDFs & images
├── .gitignore
├── README.md
└── docker-compose.yml
```

## Running the Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
