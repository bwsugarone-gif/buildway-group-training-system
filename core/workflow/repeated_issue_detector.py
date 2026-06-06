# -*- coding: utf-8 -*-
"""
core/workflow/repeated_issue_detector.py
Buildway AI Core — Repeated Issue Detection with Synonym Deduplication

Detects recurring issues across multiple analysis sessions.
Domain-neutral: synonym groups are configurable per vertical.
"""

import re
from collections import defaultdict
from typing import Any


# Default synonym groups — verticals can extend or replace
DEFAULT_SYNONYM_GROUPS: list[set[str]] = [
    {"delay", "late", "overdue", "behind schedule", "延誤", "遲"},
    {"safety", "hazard", "risk", "danger", "unsafe", "安全", "危險", "風險"},
    {"quality", "defect", "defective", "non-conformance", "quality issue", "質量", "缺陷"},
    {"payment", "invoice", "billing", "cost", "費用", "付款", "發票"},
    {"document", "drawing", "plan", "specification", "圖則", "文件", "規格"},
    {"communication", "coordination", "meeting", "溝通", "協調", "會議"},
]


def _build_word_to_group(synonym_groups: list[set[str]]) -> dict[str, int]:
    """Build a mapping from word -> group index."""
    mapping = {}
    for idx, group in enumerate(synonym_groups):
        for word in group:
            mapping[word.lower()] = idx
    return mapping


def extract_risk_groups(
    text: str,
    synonym_groups: list[set[str]] | None = None,
) -> set[int]:
    """
    Extract which synonym groups are mentioned in the text.

    Returns a set of group indices.
    """
    groups = synonym_groups or DEFAULT_SYNONYM_GROUPS
    word_to_group = _build_word_to_group(groups)
    text_lower = text.lower()
    found = set()
    for word, group_idx in word_to_group.items():
        if word in text_lower:
            found.add(group_idx)
    return found


def detect_repeated_issues(
    sessions: list[dict[str, Any]],
    min_occurrences: int = 2,
    synonym_groups: list[set[str]] | None = None,
    text_field: str = "analysis_summary",
) -> list[dict[str, Any]]:
    """
    Detect issues that appear repeatedly across sessions.

    Args:
        sessions: List of session dicts (from session_memory).
        min_occurrences: Minimum times an issue must appear to be flagged.
        synonym_groups: Custom synonym groups (uses DEFAULT_SYNONYM_GROUPS if None).
        text_field: Which field in each session to analyse.

    Returns:
        List of dicts with keys: group_idx, keywords, occurrences, sessions.
    """
    groups = synonym_groups or DEFAULT_SYNONYM_GROUPS
    group_sessions: dict[int, list[str]] = defaultdict(list)

    for session in sessions:
        text = str(session.get(text_field) or "")
        if not text.strip():
            continue
        found_groups = extract_risk_groups(text, groups)
        session_id = session.get("session_id", "unknown")
        for gidx in found_groups:
            group_sessions[gidx].append(session_id)

    repeated = []
    for gidx, session_ids in group_sessions.items():
        # Deduplicate session IDs
        unique_sessions = list(dict.fromkeys(session_ids))
        if len(unique_sessions) >= min_occurrences:
            repeated.append({
                "group_idx": gidx,
                "keywords": sorted(groups[gidx]),
                "occurrences": len(unique_sessions),
                "sessions": unique_sessions,
            })

    repeated.sort(key=lambda r: r["occurrences"], reverse=True)
    return repeated


def summarise_repeated_issues(
    repeated: list[dict[str, Any]],
) -> str:
    """Format repeated issues as a human-readable summary."""
    if not repeated:
        return "No repeated issues detected."

    lines = [f"Repeated issues detected ({len(repeated)} pattern(s)):"]
    for item in repeated:
        keywords = ", ".join(item["keywords"][:5])
        lines.append(
            f"  - [{item['occurrences']}x] Keywords: {keywords} "
            f"(sessions: {', '.join(item['sessions'][:3])}{'...' if len(item['sessions']) > 3 else ''})"
        )
    return "\n".join(lines)
