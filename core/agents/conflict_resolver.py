# -*- coding: utf-8 -*-
"""
core/agents/conflict_resolver.py
Buildway AI Core — Multi-Agent Conflict Resolver

When multiple agents produce conflicting assessments (e.g., one says low risk,
another says high risk), this module detects and surfaces those conflicts
for human review.
"""

import re
from typing import Any


# Risk level ordering (higher index = higher severity)
RISK_ORDER = ["none", "low", "medium", "high", "critical"]

# Synonyms mapping to canonical levels
RISK_SYNONYMS: dict[str, str] = {
    # English
    "none": "none", "no risk": "none",
    "low": "low", "minor": "low", "minimal": "low",
    "medium": "medium", "moderate": "medium", "mid": "medium",
    "high": "high", "major": "high", "significant": "high",
    "critical": "critical", "urgent": "critical", "severe": "critical",
    # Traditional Chinese
    "無": "none", "無風險": "none",
    "低": "low", "低風險": "low",
    "中": "medium", "中風險": "medium",
    "高": "high", "高風險": "high",
    "緊急": "critical", "極高": "critical",
}


def _normalise_risk(raw: str) -> str:
    """Normalise a raw risk string to a canonical level."""
    cleaned = str(raw or "").strip().lower()
    return RISK_SYNONYMS.get(cleaned, RISK_SYNONYMS.get(raw.strip(), "unknown"))


def _risk_rank(level: str) -> int:
    try:
        return RISK_ORDER.index(_normalise_risk(level))
    except ValueError:
        return -1


def detect_conflicts(agent_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Detect conflicts across agent results.

    Args:
        agent_results: List of dicts, each with keys:
            agent_id, agent_name, risk_level, summary (optional).

    Returns:
        Dict with keys: has_conflict, conflict_type, details, recommended_level, notes.
    """
    if not agent_results:
        return {
            "has_conflict": False,
            "conflict_type": None,
            "details": [],
            "recommended_level": "unknown",
            "notes": ["No agent results to compare."],
        }

    levels = [(r.get("agent_id", "?"), r.get("risk_level", "unknown")) for r in agent_results]
    normalised = [(aid, _normalise_risk(lvl)) for aid, lvl in levels]
    unique_levels = {lvl for _, lvl in normalised if lvl != "unknown"}

    if len(unique_levels) <= 1:
        recommended = unique_levels.pop() if unique_levels else "unknown"
        return {
            "has_conflict": False,
            "conflict_type": None,
            "details": [],
            "recommended_level": recommended,
            "notes": ["All agents agree on risk level."],
        }

    # Conflict detected
    ranks = [_risk_rank(lvl) for _, lvl in normalised if _risk_rank(lvl) >= 0]
    max_rank = max(ranks) if ranks else 0
    recommended = RISK_ORDER[max_rank] if max_rank < len(RISK_ORDER) else "unknown"

    details = [
        {"agent_id": aid, "raw_level": lvl, "normalised": _normalise_risk(lvl)}
        for aid, lvl in levels
    ]

    # Classify conflict severity
    min_rank = min(ranks) if ranks else 0
    gap = max_rank - min_rank
    if gap >= 3:
        conflict_type = "major"
    elif gap >= 2:
        conflict_type = "moderate"
    else:
        conflict_type = "minor"

    return {
        "has_conflict": True,
        "conflict_type": conflict_type,
        "details": details,
        "recommended_level": recommended,
        "notes": [
            f"Conflict detected ({conflict_type}): agents disagree on risk level.",
            f"Conservative recommendation: use highest level '{recommended}'.",
        ],
    }


def resolve(agent_results: list[dict[str, Any]], strategy: str = "conservative") -> str:
    """
    Resolve conflicting risk levels to a single level.

    Args:
        agent_results: List of agent result dicts with 'risk_level'.
        strategy: 'conservative' (highest), 'majority', or 'average'.

    Returns:
        Resolved risk level string.
    """
    if not agent_results:
        return "unknown"

    levels = [_normalise_risk(r.get("risk_level", "")) for r in agent_results]
    valid = [l for l in levels if l in RISK_ORDER]

    if not valid:
        return "unknown"

    if strategy == "conservative":
        return max(valid, key=lambda l: RISK_ORDER.index(l))

    if strategy == "majority":
        from collections import Counter
        most_common = Counter(valid).most_common(1)
        return most_common[0][0] if most_common else "unknown"

    if strategy == "average":
        avg_rank = round(sum(RISK_ORDER.index(l) for l in valid) / len(valid))
        return RISK_ORDER[min(avg_rank, len(RISK_ORDER) - 1)]

    return max(valid, key=lambda l: RISK_ORDER.index(l))
