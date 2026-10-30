# OCR & Health Processing Architecture Flow

```
+------------------+     +-----------------------+     +-----------------------+
|  Document Input  | --> |     OCR Engine        | --> |   Report Classifier   |
| (PDF / Image)    |     | (PyTesseract / Vision)|     | (Rule / Keyword / LLM)|
+------------------+     +-----------------------+     +-----------------------+
                                                                   |
                                                                   v
+------------------+     +-----------------------+     +-----------------------+
|   Health Vault   | <-- |   Summary Generator   | <-- |     Report Parser     |
|   Storage / DB   |     |  (Clinical Insights)  |     | (Biomarker Extraction)|
+------------------+     +-----------------------+     +-----------------------+
```

## Step Details

1. **Document Input & Preprocessing**:
   - Accepts image formats (PNG, JPG) or multi-page PDFs.
   - Image deskewing, binarization, noise reduction, and resolution scaling.

2. **OCR Service (`ocr_service.py`)**:
   - Converts document layout into text strings with coordinate metadata / bounding boxes.

3. **Report Classifier (`report_classifier.py`)**:
   - Categorizes document type (e.g. Complete Blood Count, Lipid Profile, Thyroid Panel, Urine Analysis).

4. **Report Parser (`report_parser.py`)**:
   - Extracts structured key-value pairs matching test names, measured values, units, and normal reference ranges based on templates in `report_templates.json`.

5. **Report Summary (`report_summary.py`)**:
   - Analyzes extracted biomarkers against `biomarker_reference.json` to highlight out-of-range metrics and compute patient health summaries.

6. **Vault Service (`vault_service.py`)**:
   - Stores structured report records into the user health vault profile.
