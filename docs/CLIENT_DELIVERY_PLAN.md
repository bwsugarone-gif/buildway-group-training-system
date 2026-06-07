# Client Delivery Plan

## Buildway Group Training System

This release delivers the standalone Group Training System product repository.

## What Is Delivered

1. Streamlit group training application
2. SQLite-backed local demo database
3. CRM customer follow-up workflow
4. Daily activity log workflow
5. AI training review and hidden closing score workflow
6. Manager dashboard and role-based views
7. Deterministic demo dataset for client walkthroughs
8. English and Traditional Chinese UI text

## Deployment

Local / Development:

```bash
pip install -r requirements.txt
streamlit run apps/streamlit_group_training/app.py
```

Streamlit Cloud Main File:

```text
apps/streamlit_group_training/app.py
```

## Environment Variables

Optional:

```text
BUILDWAY_GROUP_TRAINING_DB=database/group_training.sqlite3
BUILDWAY_GROUP_TRAINING_CLOUD_DEMO=1
BUILDWAY_GROUP_TRAINING_DEVELOPER_MODE=1
GEMINI_API_KEY=
```

Real production secrets must be configured in the hosting platform secrets manager and must not be committed.

## Delivery Notes

- Python must remain `3.11.9`.
- The official Streamlit app is `apps/streamlit_group_training/app.py`.
- The local demo database is `database/group_training.sqlite3`.
- Placeholder demo/admin/client/API apps have been removed from the active product tree.
