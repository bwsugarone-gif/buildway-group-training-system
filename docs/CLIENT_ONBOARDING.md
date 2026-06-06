# Client Onboarding Guide

This guide covers what a new tenant needs to prepare before going live on Buildway AI Core.

---

## What the Client Needs to Prepare

### 1. WhatsApp Business API
- A verified WhatsApp Business account
- Access to the WhatsApp Business API (via Meta or an approved BSP)
- Phone number registered and approved for messaging
- Webhook URL will be provided by Buildway after tenant setup

### 2. AI API Key
- **OpenAI** — API key from https://platform.openai.com
- **Anthropic (Claude)** — API key from https://console.anthropic.com
- At least one provider is required. Both can be configured for fallback.
- The client is responsible for billing on their own API account.

### 3. FAQ Document
- A list of common customer questions and standard answers
- **Recommended format: Excel (.xlsx) or CSV** with structured columns (see FAQ Data Template below)
- Alternative formats: plain text, Word, or PDF
- Used to build the tenant's RAG knowledge base
- Minimum recommended: 20–50 Q&A pairs

#### FAQ Data Template

Prepare your FAQ as an Excel or CSV file with the following columns:

| Column | Description |
|---|---|
| Category | Topic group, e.g. MOQ, Shipping, Payment |
| Question | Customer question text |
| Standard Answer | Approved reply for this question |
| Can Auto Reply | Yes / No — whether AI can reply without human review |
| Need Human Approval | Yes / No — whether staff must approve before sending |
| Risk Level | Low / Medium / High |
| Notes | Internal notes, e.g. "Do not quote exact price" |

**Example row:**
```
Category: MOQ
Question: What is your MOQ?
Standard Answer: Our MOQ depends on product model. Please share the model number and quantity for confirmation.
Can Auto Reply: Yes
Need Human Approval: No
Risk Level: Low
Notes: Do not quote exact price.
```

### 4. Product Catalog
- Full product or service listing
- Include: product name, description, SKU/code, price range
- Format: Excel, CSV, or PDF
- Used for AI product lookup and recommendation

### 5. MOQ / Shipping / Payment Terms
- Minimum order quantities per product (if applicable)
- Shipping zones, lead times, and courier options
- Accepted payment methods and terms (e.g., T/T 30 days, PayPal)
- This information is loaded into the knowledge base for AI reference

### 6. Reply Templates
- Standard reply templates for common scenarios:
  - Order confirmation
  - Shipping update
  - Out-of-stock notice
  - Escalation to human agent
  - After-hours auto-reply
- Format: plain text or Word document
- Templates are used in Phase 1 (AI Assist) and Phase 2 (Auto Mode)

### 7. Optional: Historical Chat Examples
- Sample past customer conversations (anonymized)
- Helps AI learn company tone and response style
- Format: Excel, CSV, or plain text

---

## Data Preparation Summary

Client needs to prepare:
- **FAQ** (Excel / CSV / DOCX / PDF) — structured FAQ template recommended
- **Product Catalog** (Excel / CSV / PDF)
- **MOQ Rules** (Excel / DOCX / PDF)
- **Shipping Terms** (DOCX / PDF)
- **Payment Terms** (DOCX / PDF)
- **Reply Templates** (DOCX / TXT)
- **Optional: Historical chat examples** (Excel / CSV / TXT)

**Note:** If using Buildway Hosted database mode, client does not need to prepare a database server. Client still needs to prepare all business data listed above.

---

## Onboarding Steps

1. **Tenant Registration** — Buildway creates the tenant account and provides login credentials
2. **API Key Setup** — Client submits WhatsApp API and AI API keys via the admin portal (encrypted at rest)
3. **Knowledge Base Upload** — Client uploads FAQ, product catalog, and terms documents
4. **Template Configuration** — Reply templates are loaded and reviewed
5. **Test Run** — Buildway runs a test conversation to verify AI responses
6. **Go Live** — WhatsApp webhook is activated; AI Assist Mode is enabled

---

## Phase 1 Go-Live Checklist

- [ ] WhatsApp Business API credentials submitted
- [ ] AI API key submitted (OpenAI or Anthropic)
- [ ] FAQ document uploaded (min. 20 Q&A)
- [ ] Product catalog uploaded
- [ ] MOQ / shipping / payment terms provided
- [ ] Reply templates provided (min. 5 scenarios)
- [ ] Test conversation completed and approved
- [ ] Staff trained on AI Assist dashboard

---

## Support

For onboarding support, contact your Buildway account manager.
