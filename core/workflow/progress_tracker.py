# -*- coding: utf-8 -*-
"""
core/workflow/progress_tracker.py
Buildway AI Core — Workflow Progress Tracker

Tracks multi-step workflow progress in memory or JSON.
Domain-neutral.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


STEP_STATUSES = ["pending", "running", "completed", "failed", "skipped"]


class ProgressTracker:
    """
    Tracks progress of a multi-step workflow.

    Usage:
        tracker = ProgressTracker(steps=["load", "ocr", "analyse", "report"])
        tracker.start("load")
        tracker.complete("load")
        tracker.fail("ocr", error="Tesseract not found")
        print(tracker.summary())
    """

    def __init__(self, steps: list[str], workflow_id: str = ""):
        self.workflow_id = workflow_id or f"WF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.steps: dict[str, dict[str, Any]] = {
            step: {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "error": None,
                "metadata": {},
            }
            for step in steps
        }
        self.step_order = list(steps)
        self.created_at = datetime.now().isoformat(timespec="seconds")

    def start(self, step: str, metadata: dict | None = None) -> None:
        """Mark a step as running."""
        if step not in self.steps:
            raise KeyError(f"Unknown step: {step}")
        self.steps[step]["status"] = "running"
        self.steps[step]["started_at"] = datetime.now().isoformat(timespec="seconds")
        if metadata:
            self.steps[step]["metadata"].update(metadata)

    def complete(self, step: str, metadata: dict | None = None) -> None:
        """Mark a step as completed."""
        if step not in self.steps:
            raise KeyError(f"Unknown step: {step}")
        self.steps[step]["status"] = "completed"
        self.steps[step]["completed_at"] = datetime.now().isoformat(timespec="seconds")
        if metadata:
            self.steps[step]["metadata"].update(metadata)

    def fail(self, step: str, error: str = "", metadata: dict | None = None) -> None:
        """Mark a step as failed."""
        if step not in self.steps:
            raise KeyError(f"Unknown step: {step}")
        self.steps[step]["status"] = "failed"
        self.steps[step]["completed_at"] = datetime.now().isoformat(timespec="seconds")
        self.steps[step]["error"] = error
        if metadata:
            self.steps[step]["metadata"].update(metadata)

    def skip(self, step: str, reason: str = "") -> None:
        """Mark a step as skipped."""
        if step not in self.steps:
            raise KeyError(f"Unknown step: {step}")
        self.steps[step]["status"] = "skipped"
        self.steps[step]["error"] = reason

    def get_status(self, step: str) -> str:
        """Get the status of a step."""
        return self.steps.get(step, {}).get("status", "unknown")

    def is_complete(self) -> bool:
        """Return True if all steps are completed or skipped."""
        return all(
            s["status"] in {"completed", "skipped"}
            for s in self.steps.values()
        )

    def has_failures(self) -> bool:
        """Return True if any step failed."""
        return any(s["status"] == "failed" for s in self.steps.values())

    def summary(self) -> str:
        """Return a human-readable progress summary."""
        lines = [f"Workflow: {self.workflow_id}"]
        for step in self.step_order:
            info = self.steps[step]
            status = info["status"].upper()
            error = f" — {info['error']}" if info.get("error") else ""
            lines.append(f"  [{status}] {step}{error}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialise tracker state to a dict."""
        return {
            "workflow_id": self.workflow_id,
            "created_at": self.created_at,
            "steps": self.steps,
            "step_order": self.step_order,
            "is_complete": self.is_complete(),
            "has_failures": self.has_failures(),
        }

    def save(self, path: Path) -> None:
        """Save tracker state to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "ProgressTracker":
        """Load tracker state from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        tracker = cls(steps=data["step_order"], workflow_id=data["workflow_id"])
        tracker.steps = data["steps"]
        tracker.created_at = data.get("created_at", "")
        return tracker
