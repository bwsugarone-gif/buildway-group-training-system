# -*- coding: utf-8 -*-
"""
core/memory/session_memory.py
Buildway AI Core — Lightweight Session Memory Manager

Storage: JSON file (data/session_memory.json)
No database, no login, no cloud.

Session record schema:
{
    "session_id":        "SES-20260516-143022-abc1",
    "project_ref":       "BW-001",
    "upload_time":       "2026-05-16T14:30:22",
    "file_names":        ["doc.pdf", "photo.jpg"],
    "file_types":        ["pdf", "image"],
    "selected_agents":   ["agent_a", "agent_b"],
    "risk_level":        "high",
    "analysis_summary":  "First 300 chars...",
    "analysis_type":     "document_analysis",
    "question":          "What are the key issues?"
}

Rules:
- Keep only the latest 5 sessions per project_ref.
- Total cap: 50 sessions across all projects (oldest pruned first).
- If file is missing or corrupt, return empty list — never crash.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_MEM_FILE = _DATA_DIR / "session_memory.json"
_MAX_PER_PROJECT = 5
_MAX_TOTAL = 50
_SUMMARY_CHARS = 300


def _ensure_dir():
    _DATA_DIR.mkdir(exist_ok=True)


def _load_all() -> list:
    """Load all sessions from JSON. Returns [] on any error."""
    _ensure_dir()
    if not _MEM_FILE.exists():
        return []
    try:
        data = json.loads(_MEM_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_all(sessions: list) -> None:
    _ensure_dir()
    _MEM_FILE.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_session(
    project_ref: str,
    file_names: list[str],
    file_types: list[str],
    selected_agents: list[str],
    risk_level: str,
    analysis_summary: str,
    analysis_type: str = "",
    question: str = "",
    extra: dict | None = None,
) -> str:
    """Save a new session record. Returns the new session_id."""
    session_id = f"SES-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
    record = {
        "session_id": session_id,
        "project_ref": str(project_ref or "").strip(),
        "upload_time": datetime.now().isoformat(timespec="seconds"),
        "file_names": list(file_names or []),
        "file_types": list(file_types or []),
        "selected_agents": list(selected_agents or []),
        "risk_level": str(risk_level or ""),
        "analysis_summary": str(analysis_summary or "")[:_SUMMARY_CHARS],
        "analysis_type": str(analysis_type or ""),
        "question": str(question or ""),
    }
    if extra and isinstance(extra, dict):
        record.update(extra)

    sessions = _load_all()
    sessions.append(record)

    # Prune: keep latest 5 per project
    ref = record["project_ref"]
    project_sessions = [s for s in sessions if s.get("project_ref") == ref]
    if len(project_sessions) > _MAX_PER_PROJECT:
        oldest = sorted(project_sessions, key=lambda s: s.get("upload_time", ""))[
            : len(project_sessions) - _MAX_PER_PROJECT
        ]
        oldest_ids = {s["session_id"] for s in oldest}
        sessions = [s for s in sessions if s.get("session_id") not in oldest_ids]

    # Prune: global cap
    if len(sessions) > _MAX_TOTAL:
        sessions = sorted(sessions, key=lambda s: s.get("upload_time", ""))
        sessions = sessions[len(sessions) - _MAX_TOTAL :]

    _save_all(sessions)
    return session_id


def load_sessions(project_ref: str | None = None) -> list:
    """Load sessions, optionally filtered by project_ref."""
    sessions = _load_all()
    if project_ref:
        sessions = [s for s in sessions if s.get("project_ref") == str(project_ref).strip()]
    return sorted(sessions, key=lambda s: s.get("upload_time", ""), reverse=True)


def get_session(session_id: str) -> dict | None:
    """Get a single session by ID."""
    for s in _load_all():
        if s.get("session_id") == session_id:
            return s
    return None


def delete_session(session_id: str) -> bool:
    """Delete a session by ID. Returns True if deleted."""
    sessions = _load_all()
    new_sessions = [s for s in sessions if s.get("session_id") != session_id]
    if len(new_sessions) == len(sessions):
        return False
    _save_all(new_sessions)
    return True


def clear_all_sessions() -> int:
    """Clear all sessions. Returns count deleted."""
    sessions = _load_all()
    count = len(sessions)
    _save_all([])
    return count
