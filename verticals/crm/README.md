# CRM Vertical — AI Assist

This vertical implements AI-assisted customer relationship management for Buildway AI Core.

---

## Phase 1 — WhatsApp AI Assist Mode

**Goal:** AI drafts replies; human staff reviews and sends. No autonomous sending.

### Features

| Feature | Description | Status |
|---|---|---|
| WhatsApp AI Assist | AI drafts reply suggestions for incoming WhatsApp messages | Phase 1 |
| RAG FAQ | Knowledge base search using tenant's FAQ documents | Phase 1 |
| Customer Memory | Per-customer conversation history and summary | Phase 1 |
| AI Draft Reply | LLM generates reply draft based on context + knowledge base | Phase 1 |
| Human Approval | Staff reviews AI draft before sending | Phase 1 |

### Flow

```
Customer sends WhatsApp message
    → services/whatsapp/ receives inbound message
    → core/memory/ loads customer history
    → core/rag/ searches tenant knowledge base (FAQ, product catalog)
    → verticals/crm/ builds prompt with context
    → LLM generates draft reply (using tenant's API key)
    → Draft shown in apps/streamlit_admin/ for staff review
    → Staff approves / edits / rejects
    → Approved reply sent via WhatsApp API
    → core/memory/ saves session and message
    → core/actions/ logs any follow-up actions
```

---

## Phase 2 — WhatsApp Auto Mode

**Goal:** AI handles routine queries autonomously. Escalates to human when confidence is low.

- Auto-reply engine with confidence threshold gating
- After-hours auto-reply
- Fallback to human agent
- Session summary generation

---

## Module Structure

```
verticals/crm/
├── README.md           # This file
├── __init__.py         # (to be created)
├── agents/             # CRM-specific agent definitions
├── prompts/            # Reply draft prompt templates
├── rules/              # Escalation rules, confidence thresholds
└── tests/              # CRM vertical tests
```

---

## Rules

- CRM logic stays in `verticals/crm/` — never in `core/`
- All data operations must include `tenant_id`
- AI never sends messages without human approval in Phase 1
- Tenant's own API key is used for all LLM calls
