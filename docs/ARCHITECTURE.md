# Buildway AI Core — Architecture

## Overview

Buildway AI Core is a layered AI operating system designed for multi-industry deployment.
The architecture separates generic infrastructure (core) from domain-specific logic (verticals).

```
┌─────────────────────────────────────────────────────────┐
│                        APPS LAYER                        │
│          streamlit_demo /  api_server (future)           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    VERTICALS LAYER                       │
│   construction/    crm/    document_ai/  (extensible)   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                      CORE LAYER                          │
│  memory  rag  ocr  document_processing  agents           │
│  workflow  actions  reports  security                    │
└─────────────────────────────────────────────────────────┘
```

## Core Layer

The core layer contains all domain-neutral modules. No industry-specific logic belongs here.

| Module | Responsibility |
|---|---|
| `core/memory/` | Session memory (JSON, no DB) |
| `core/rag/` | RAG lite — local JSON index, keyword search |
| `core/ocr/` | OCR via Tesseract + pdf2image |
| `core/document_processing/` | File loading (PDF, DOCX, XLSX, images) |
| `core/agents/` | Agent routing framework, evidence scoring, conflict resolution |
| `core/workflow/` | Progress tracking, repeated issue detection |
| `core/actions/` | Action item CRUD |
| `core/reports/` | PDF generation via ReportLab |
| `core/security/` | Placeholder — Phase 2 |

## Verticals Layer

Each vertical extends the core for a specific industry.

### Construction (`verticals/construction/`)
- Agent definitions: Safety, PM, QS, Engineering, Foreman, Material, Drafting, Surveying, Accounting
- Source: HK-AICOS (https://github.com/bwsugarone-gif/hk-aicos)

### CRM (`verticals/crm/`)
- Customer memory, customer RAG, reply draft agent, escalation rules
- Status: Initial placeholder

### Document AI (`verticals/document_ai/`)
- Status: Placeholder

## Data Flow

```
User uploads file
    → file_loader.load_file()
    → ocr_engine.extract_text_with_ocr()  (if scanned)
    → evidence_confidence.score_files()   (gate check)
    → rag_manager.search()                (context retrieval)
    → AgentRouter.build_prompt()          (prompt construction)
    → LLM API call
    → conflict_resolver.detect_conflicts()
    → report_generator.generate_pdf()
    → action_manager.add_action_item()
    → session_memory.save_session()
```

## Design Principles

1. **No database** — JSON files only for MVP. Easy to migrate later.
2. **No cloud lock-in** — All processing is local by default.
3. **Vertical isolation** — Core never imports from verticals.
4. **Python 3.11.x** — No version upgrades without explicit approval.
5. **Streamlit first** — Demo app uses Streamlit. API server is Phase 2.

## Adding a New Vertical

1. Create `verticals/your_vertical/__init__.py`
2. Define domain-specific agents, rules, and extensions
3. Import from `core/` as needed
4. Never modify `core/` for vertical-specific logic
