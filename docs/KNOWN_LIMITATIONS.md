# Known Limitations

## Core

### RAG
- Uses simple keyword overlap scoring (no embeddings, no semantic search)
- No vector database — all search is in-memory from JSON index
- Large document sets (>500 docs) will be slow

### OCR
- Requires Tesseract to be installed locally (`apt install tesseract-ocr` or Windows installer)
- Requires `pdf2image` and Poppler for PDF OCR
- OCR quality depends on scan resolution (recommend 200+ DPI)
- Limited to first 20 pages for large scanned PDFs

### Memory
- JSON file storage only — not suitable for concurrent multi-user access
- No encryption at rest
- Session cap: 50 total, 5 per project

### Reports
- Requires `NotoSansTC-Regular.ttf` font file in `assets/fonts/` for CJK rendering
- Falls back to Helvetica (no CJK) if font is missing

### Security
- No authentication or authorisation in Phase 1
- API keys stored in `.env` file — do not commit to version control

## Verticals

### Construction
- Agent instructions are in Traditional Chinese — English support requires translation
- HK regulation references are HK-specific (BD, EMSD, CEDD, etc.)

### CRM
- Placeholder only — not production-ready
- No email integration in Phase 1

### Document AI
- Placeholder only — not implemented
