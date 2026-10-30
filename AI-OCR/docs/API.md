# AI-OCR Health Vault API Specification

## Endpoints Overview

### Health Check
- `GET /health`
  - Returns service status and system connectivity.

### Health Vault APIs

#### 1. Upload & Process Lab Report
- `POST /api/vault/upload`
  - **Payload**: `multipart/form-data` with `file` (PDF/PNG/JPEG)
  - **Returns**: `ReportUploadResponse` containing report ID, classified report type, extracted biomarkers, and clinical summary.

#### 2. Get Report Details
- `GET /api/vault/reports/{report_id}`
  - **Returns**: Detailed view of a parsed report, including raw OCR text, structured biomarker key-value pairs, and reference comparison.

#### 3. List Reports
- `GET /api/vault/reports`
  - **Parameters**: `page`, `limit`, `category`
  - **Returns**: Array of summarized reports stored in the user's Health Vault.

#### 4. Summarize Biomarkers
- `POST /api/vault/summarize`
  - **Payload**: List of report IDs or structured biomarker data.
  - **Returns**: Health trend summary and flagged abnormal values.
