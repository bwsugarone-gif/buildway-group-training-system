# -*- coding: utf-8 -*-
"""
core/actions/action_manager.py
Buildway AI Core — Action Item Storage and Helpers

Generic action tracker. No domain-specific logic.
Storage: JSON file (data/action_items.json)
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent.parent
_DATA_DIR = _BASE_DIR / "data"
_ACTION_FILE = _DATA_DIR / "action_items.json"

STATUSES = ["pending", "in_progress", "completed", "deferred"]
PRIORITIES = ["high", "medium", "low"]
OPEN_STATUSES = {"pending", "in_progress", "deferred"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_action_file() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _ACTION_FILE.exists():
        _ACTION_FILE.write_text("[]", encoding="utf-8")


def _read_json(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("action_items.json must be a list.")
    return data


def load_action_items(action_file: Path | None = None) -> list:
    """Load action items. Auto-create an empty list when missing."""
    path = action_file or _ACTION_FILE
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    return _read_json(path)


def save_action_items(items: list, action_file: Path | None = None) -> None:
    path = action_file or _ACTION_FILE
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(list(items or []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def backup_action_items(action_file: Path | None = None) -> Path:
    """Create a timestamped backup of the action items file."""
    path = action_file or _ACTION_FILE
    if not path.exists():
        return path
    backup_path = path.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.json")
    shutil.copy2(path, backup_path)
    return backup_path


def add_action_item(
    title: str,
    description: str = "",
    priority: str = "medium",
    assigned_to: str = "",
    due_date: str = "",
    project_ref: str = "",
    source_agent: str = "",
    tags: list[str] | None = None,
    action_file: Path | None = None,
) -> dict:
    """
    Add a new action item.

    Returns the created action item dict.
    """
    item = {
        "id": f"ACT-{uuid.uuid4().hex[:8].upper()}",
        "title": str(title or "").strip(),
        "description": str(description or "").strip(),
        "priority": priority if priority in PRIORITIES else "medium",
        "status": "pending",
        "assigned_to": str(assigned_to or "").strip(),
        "due_date": str(due_date or "").strip(),
        "project_ref": str(project_ref or "").strip(),
        "source_agent": str(source_agent or "").strip(),
        "tags": list(tags or []),
        "created_at": _now(),
        "updated_at": _now(),
    }
    items = load_action_items(action_file)
    items.append(item)
    save_action_items(items, action_file)
    return item


def update_action_item(
    item_id: str,
    updates: dict,
    action_file: Path | None = None,
) -> dict | None:
    """
    Update fields on an existing action item.

    Returns the updated item, or None if not found.
    """
    items = load_action_items(action_file)
    for item in items:
        if item.get("id") == item_id:
            for key, value in updates.items():
                if key not in {"id", "created_at"}:
                    item[key] = value
            item["updated_at"] = _now()
            save_action_items(items, action_file)
            return item
    return None


def delete_action_item(item_id: str, action_file: Path | None = None) -> bool:
    """Delete an action item by ID. Returns True if deleted."""
    items = load_action_items(action_file)
    new_items = [i for i in items if i.get("id") != item_id]
    if len(new_items) == len(items):
        return False
    save_action_items(new_items, action_file)
    return True


def get_open_items(project_ref: str | None = None, action_file: Path | None = None) -> list:
    """Return all open (non-completed) action items, optionally filtered by project."""
    items = load_action_items(action_file)
    result = [i for i in items if i.get("status") in OPEN_STATUSES]
    if project_ref:
        result = [i for i in result if i.get("project_ref") == project_ref]
    return result


def get_items_by_project(project_ref: str, action_file: Path | None = None) -> list:
    """Return all action items for a given project."""
    items = load_action_items(action_file)
    return [i for i in items if i.get("project_ref") == project_ref]
