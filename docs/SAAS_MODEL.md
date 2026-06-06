# Buildway AI Core — SaaS Model

## Overview

Buildway AI Core operates as a **BYOK (Bring Your Own Key) SaaS platform**.
Buildway provides the platform infrastructure; each client tenant brings their own API credentials and is responsible for their own token costs.

---

## Model Summary

| Item | Responsibility |
|---|---|
| SaaS Platform | Buildway |
| WhatsApp Business API | Client (tenant) |
| AI API Key (OpenAI / Claude) | Client (tenant) |
| Token Cost | Client (tenant) |
| Data Isolation | Buildway (per-tenant) |
| Platform Uptime | Buildway |

---

## How It Works

### 1. Client Brings Their Own WhatsApp API
- Each tenant registers their own WhatsApp Business API credentials.
- Credentials are stored encrypted in the `api_keys` table, scoped to `tenant_id`.
- Buildway never shares API credentials between tenants.

### 2. Client Brings Their Own AI API Key
- Tenants supply their own OpenAI or Anthropic API key.
- All LLM calls are made using the tenant's key — token costs are billed directly to the tenant's account.
- Buildway does not absorb or resell AI token costs.

### 3. Buildway Provides the Platform
- Multi-tenant SaaS infrastructure
- AI workflow engine (RAG, agents, memory, actions)
- WhatsApp integration layer
- Admin dashboard and client portal
- Onboarding and knowledge base management

### 4. Tenant Isolation
- Every database record is scoped to `tenant_id`.
- No cross-tenant data access is permitted at the application layer.
- API keys, knowledge bases, chat sessions, and usage logs are all tenant-isolated.

---

## Pricing Model (Draft)

| Tier | Description |
|---|---|
| Starter | Single tenant, limited monthly sessions |
| Business | Multi-user, full feature access |
| Enterprise | Custom SLA, dedicated support |

> Pricing is subject to change. Token costs are always passed through to the client.

---

## Security Notes

- API keys are never stored in plaintext. Use AES-256 encryption or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) in production.
- `.env` files are for local development only. Never commit real keys.
- See `.env.example` for required environment variable names.

---

## Phase Rollout

- **Phase 1** — AI Assist Mode (staff-assisted, AI drafts replies)
- **Phase 2** — WhatsApp Auto Mode (AI handles routine queries autonomously)
- **Phase 3** — ERP / Inventory API integration
