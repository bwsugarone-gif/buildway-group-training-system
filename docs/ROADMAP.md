# Buildway AI Core — Roadmap

## Phase 1 — CRM AI Assist Mode

**Goal:** Staff-assisted AI. AI drafts replies; human reviews and sends.

- [ ] CRM vertical — customer memory
- [ ] CRM vertical — RAG knowledge base (FAQ, product catalog)
- [ ] CRM vertical — reply draft agent
- [ ] CRM vertical — escalation rules
- [ ] WhatsApp inbound message handler (AI Assist mode)
- [ ] Admin dashboard — conversation view
- [ ] Admin dashboard — reply approval workflow
- [ ] Tenant onboarding flow
- [ ] Knowledge base upload and indexing
- [ ] Usage log tracking (tokens per tenant)

## Phase 2 — WhatsApp Auto Mode

**Goal:** AI handles routine queries autonomously without staff intervention.

- [ ] Auto-reply engine (confidence threshold gating)
- [ ] Fallback to human agent when confidence is low
- [ ] After-hours auto-reply
- [ ] Session summary generation
- [ ] Multi-turn conversation memory
- [ ] REST API server (FastAPI)
- [ ] Security layer (API key auth, rate limiting, input sanitisation)
- [ ] Vector embeddings for RAG (replace keyword search)
- [ ] Audit logging
- [ ] Client portal (streamlit_client)

## Phase 3 — ERP / Inventory API Integration

**Goal:** Connect AI workflows to inventory and supplier systems.

- [ ] ERP vertical — inventory lookup
- [ ] ERP vertical — purchase order status
- [ ] ERP vertical — supplier management
- [ ] Webhook support for ERP events
- [ ] Cloud storage integration (S3 / GCS)
- [ ] Multi-language support (beyond CJK)
- [ ] Usage analytics dashboard

---

## Vertical Status

| Vertical | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| CRM | 🔲 Build | Enhance | SaaS |
| Construction | ✅ Active (HK-AICOS) | Enhance | SaaS |
| Document AI | 🔲 Placeholder | Build | SaaS |
| ERP | — | — | 🔲 Build |

---

## Core Rules (Non-Negotiable)

1. `core/` never imports from `verticals/`
2. Construction logic stays in `verticals/construction/`
3. CRM logic stays in `verticals/crm/`
4. Python 3.11.x — no version upgrades without explicit approval
5. No hardcoded API keys anywhere in the codebase
6. HK-AICOS repo is not modified by this project
