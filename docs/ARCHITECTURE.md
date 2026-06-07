# Buildway Group Training System Architecture

## Overview

Buildway Group Training System is a standalone Streamlit product. The repository keeps the application layer focused on one official entry point and keeps group training domain logic in `verticals/group_training/`.

## Official Entry Point

```text
apps/streamlit_group_training/app.py
```

## Layers

```text
apps/
  streamlit_group_training/      # Streamlit UI, i18n, app-level services

verticals/
  group_training/                # Domain models, repository interfaces, services, agents

core/                            # Shared technical helpers
services/                        # External service placeholders/helpers
database/                        # SQLite demo DB and reference schema
tests/                           # Group training tests
```

## Application Layer

`apps/streamlit_group_training/app.py` owns the Streamlit UI, navigation, login panel, role-based views, demo controls, OCR intake screens, CRM tables, daily log forms, AI insights, and dashboard rendering.

## Domain Layer

`verticals/group_training/` owns:

- User, team, customer, daily log, AI review, and closing score models
- Authentication service integration
- Customer service
- Daily log service
- Dashboard service
- SQLite repository
- Training and closing score agents

## Data Layer

The local demo database is:

```text
database/group_training.sqlite3
```

The repository schema is initialized by `verticals/group_training/services/sqlite_repository.py`.

## Design Rules

1. Python remains pinned to 3.11.9.
2. Streamlit Cloud Main File remains `apps/streamlit_group_training/app.py`.
3. Group training business logic stays in `verticals/group_training/`.
4. Streamlit UI code stays in `apps/streamlit_group_training/`.
5. SQLite schema changes require explicit approval.
6. Login, RBAC, i18n, and demo dataset behavior are product-critical and should not be changed during structural cleanup.
