# Database

This folder contains the local SQLite demo database and the reference schema file for the Buildway Group Training System.

## Active SQLite Database

```text
database/group_training.sqlite3
```

The Streamlit app uses this database by default through `verticals/group_training/services/sqlite_repository.py`.

The path can be overridden with:

```text
BUILDWAY_GROUP_TRAINING_DB
```

## Active Tables

The SQLite repository initializes these product tables:

- `users`
- `teams`
- `customers`
- `customer_followups`
- `daily_activity_logs`
- `ai_training_reviews`
- `closing_scores`

## Reference Schema

`schema.sql` is kept as a reference schema draft. It is not an automatically applied migration file.

## Notes

- Do not commit real API keys or production credentials.
- Do not change the SQLite schema without explicit approval.
