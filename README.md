# Buildway Group Training System

Buildway Group Training System is a standalone Streamlit product for insurance group training, CRM follow-up tracking, daily activity logging, AI training reviews, manager dashboards, OCR-assisted customer intake, and demo dataset walkthroughs.

This repository is no longer a general Buildway AI Core demo repository. The official application entry point is the Group Training Streamlit app.

## Streamlit Cloud

Streamlit Cloud Main File:

```text
apps/streamlit_group_training/app.py
```

## Quick Start

```bash
pip install -r requirements.txt
streamlit run apps/streamlit_group_training/app.py
```

## Product Scope

- CRM customer tracking and follow-up records
- Daily activity logs for agents
- AI training review generation
- Hidden closing score dashboard for managers
- Role-based views for Admin, Manager, and Agent
- SQLite-backed Phase 1 demo database
- Deterministic demo dataset for walkthroughs
- English and Traditional Chinese UI text

## Repository Structure

```text
apps/
  streamlit_group_training/      # Official Streamlit app
core/                            # Shared technical helpers used by the product
database/
  group_training.sqlite3         # Local SQLite demo database
  schema.sql                     # Reference schema draft
docs/                            # Product and delivery documentation
services/                        # External service placeholders/helpers
tests/                           # Group training test suite
verticals/
  group_training/                # Group training domain models, services, agents
```

## Requirements

- Python 3.11.9
- Dependencies listed in `requirements.txt`

## Database

The local demo database is:

```text
database/group_training.sqlite3
```

The app can override the database path with:

```text
BUILDWAY_GROUP_TRAINING_DB
```

## Rules

1. Keep Python pinned to 3.11.9.
2. Keep Streamlit Cloud Main File as `apps/streamlit_group_training/app.py`.
3. Do not hardcode real API keys or production secrets.
4. Preserve tenant-scoped data access.
5. Keep group training business logic inside `verticals/group_training/` and the Streamlit product app inside `apps/streamlit_group_training/`.

## Licence

Buildway Tech (HK) Limited - Internal use
