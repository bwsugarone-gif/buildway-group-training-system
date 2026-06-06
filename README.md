# Buildway AI Core

**Buildway AI Core** is a general AI operation platform for multi-industry SaaS deployment.

It provides the shared infrastructure for AI-assisted workflows across verticals including construction, CRM, document processing, and ERP.

---

## What It Does

- **CRM AI Assist** — AI drafts replies for customer enquiries; staff review and send
- **WhatsApp Auto Mode** — AI handles routine queries autonomously (Phase 2)
- **Document AI** — Intelligent document parsing, OCR, and extraction
- **Construction AI** — Site analysis, safety checks, QS, and reporting (via HK-AICOS)
- **ERP Integration** — Inventory and supplier management (Phase 3)

---

## Supported Verticals

| Vertical | Status |
|---|---|
| CRM | Phase 1 — AI Assist |
| Construction | Active (HK-AICOS) |
| Document AI | Placeholder |
| ERP | Phase 3 Placeholder |

---

## SaaS Model

- Clients bring their own **WhatsApp Business API**
- Clients bring their own **AI API key** (OpenAI / Claude)
- Buildway provides the **SaaS platform and workflow engine**
- Token costs are the **client's responsibility**
- Each client is a **fully isolated tenant**

See [docs/SAAS_MODEL.md](docs/SAAS_MODEL.md) for full details.

---

## Architecture

```
buildway-ai-core/
├── core/                    # Domain-neutral AI modules
│   ├── memory/              # Session memory
│   ├── rag/                 # RAG retrieval
│   ├── agents/              # Agent routing
│   ├── workflow/            # Workflow tools
│   ├── actions/             # Action tracking
│   ├── reports/             # PDF generation
│   ├── document_processing/ # File loading and parsing
│   ├── ocr/                 # OCR extraction
│   └── security/            # Auth and security (Phase 2)
│
├── services/                # External service integrations
│   ├── whatsapp/            # WhatsApp Business API
│   ├── email/               # Email integration
│   ├── speech_to_text/      # STT transcription
│   ├── ocr/                 # Cloud OCR
│   └── pdf/                 # PDF service wrapper
│
├── verticals/               # Industry-specific modules
│   ├── construction/        # HK-AICOS construction agents
│   ├── crm/                 # CRM AI Assist
│   ├── document_ai/         # Document intelligence
│   └── erp/                 # ERP integration (Phase 3)
│
├── apps/                    # Application layer
│   ├── streamlit_admin/     # Operator admin dashboard
│   ├── streamlit_client/    # Client-facing portal
│   └── api_server/          # REST API (Phase 2)
│
├── database/                # Schema drafts
├── docs/                    # Documentation
└── tests/                   # Test suite
```

---

## Roadmap

- **Phase 1** — CRM AI Assist Mode (staff-assisted, AI drafts replies)
- **Phase 2** — WhatsApp Auto Mode (AI handles routine queries autonomously)
- **Phase 3** — ERP / Inventory API integration

See [docs/ROADMAP.md](docs/ROADMAP.md) for full roadmap.

---

## Tech Stack

- Python 3.11.9
- Streamlit (admin and client apps)
- ReportLab (PDF generation)
- pypdf / pytesseract (document processing)
- OpenAI / Anthropic (LLM — client-supplied keys)
- SQLite for the Phase 1.2 client demo (`database/group_training.sqlite3`)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run Phase 1.2 group training client demo
streamlit run apps/streamlit_group_training/app.py
```

---

## Rules

1. `core/` must not contain industry-specific logic
2. Construction logic stays in `verticals/construction/`
3. CRM logic stays in `verticals/crm/`
4. All tenant data must include `tenant_id`
5. API keys are never hardcoded — use `.env` only
6. See `.env.example` for required variables

---

## Version

- v0.1.0 — Initial SaaS skeleton

## Licence

Buildway Tech (HK) Limited — Internal use
