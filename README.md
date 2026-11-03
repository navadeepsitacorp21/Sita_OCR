# SITA OCR Engine & Clinical Biomarker Microservice

AI-powered medical report extraction, deterministic biomarker normalization, and clinical interpretation microservice designed for zero-data-retention external integration.

---

## 📚 Complete Documentation

- **[System Architecture & Integration Guide](docs/INTEGRATION_AND_ARCHITECTURE.md)**: Full pipeline diagrams, ONNX neural models, Supabase contracts, REST API specifications, error matrices, and client-side optimization best practices.

---

## ⚡ Quick Start for Integration Team

### Primary Microservice Endpoint
- **URL**: `https://sita-ocr.onrender.com/api/v1/ocr/process`
- **Method**: `POST`
- **Supported Encodings**: `multipart/form-data` or `application/json` (Base64)
- **Supported File Formats**: PDF, PNG, JPG, JPEG, WEBP (up to 20 MB)

#### Sample Request (Multipart)
```bash
curl -X POST https://sita-ocr.onrender.com/api/v1/ocr/process \
  -F "user_id=8f7c1234-5678-4321-abcd-ef0123456789" \
  -F "file=@sample_lft.png"
```

#### Sample Response
```json
{
  "success": true,
  "user_id": "8f7c1234-5678-4321-abcd-ef0123456789",
  "report_id": "2d513426-e041-467b-819c-be5fe4a62c0f",
  "report_type": "LFT",
  "processing_status": "completed",
  "report": { ... },
  "biomarkers": [
    {
      "id": "c46bdcff-4e0b-44e7-81ff-d4ad46ac9aee",
      "user_id": "8f7c1234-5678-4321-abcd-ef0123456789",
      "report_id": "2d513426-e041-467b-819c-be5fe4a62c0f",
      "name": "Direct Bilirubin",
      "value": 0.2,
      "unit": "mg/dL",
      "reference_min": 0.0,
      "reference_max": 0.3,
      "status": "normal",
      "confidence": 0.77
    }
  ]
}
```

---

## 🧠 Key Technical Highlights

1. **Neural OCR Stack**: RapidOCR powered by vectorized CPU ONNX models (`ch_PP-OCRv3_det` + `ch_PP-OCRv3_rec`), running with bounded memory buffers (`rec_batch_num=4`).
2. **Dual PDF Extraction**: Instant native vector text extraction via PyMuPDF (~20ms) with seamless fallback to neural OCR for scanned/rasterized documents.
3. **Stateless Microservice**: Does not store uploaded images, PDFs, or patient records on disk when called via `/api/v1/ocr/process`.
4. **Deterministic Rule Engine**: 100% reproducible parsing, unit normalization, biological range matching, and clinical pattern detection (zero LLM hallucination risk).
5. **Low Memory Footprint**: Strictly tuned to run reliably inside Render's 512 MB RAM container (`MALLOC_ARENA_MAX=2`, single-threaded ONNX execution, and proactive OS heap trimming).

