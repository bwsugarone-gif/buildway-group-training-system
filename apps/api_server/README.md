# API Server (Placeholder)

This directory is reserved for a future REST API server wrapping the Buildway AI Core.

## Planned Stack

- FastAPI
- Uvicorn
- Pydantic v2

## Planned Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/analyse` | Submit documents for AI analysis |
| GET | `/sessions/{project_ref}` | Get session history |
| POST | `/rag/index` | Index a document |
| GET | `/rag/search` | Search indexed documents |
| GET | `/actions/{project_ref}` | Get action items |
| POST | `/report/generate` | Generate PDF report |

## Status

Not yet implemented. Phase 2 roadmap item.
