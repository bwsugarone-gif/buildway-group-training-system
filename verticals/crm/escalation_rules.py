# -*- coding: utf-8 -*-
"""
verticals/crm/escalation_rules.py
Buildway AI Core — CRM Vertical: Escalation Rules

Defines rules for when a customer issue should be escalated
to a human agent or senior team member.
"""

from typing import Any


# Escalation levels
ESCALATION_LEVELS = {
    0: "none",
    1: "monitor",
    2: "flag",
    3: "escalate",
    4: "urgent",
}

# Default keyword triggers for escalation
DEFAULT_ESCALATION_KEYWORDS: dict[str, int] = {
    # Level 4 — Urgent
    "legal action": 4,
    "lawsuit": 4,
    "sue": 4,
    "lawyer": 4,
    "court": 4,
    "fraud": 4,
    "scam": 4,
    "police": 4,

    # Level 3 — Escalate
    "cancel": 3,
    "refund": 3,
    "complaint": 3,
    "unacceptable": 3,
    "terrible": 3,
    "worst": 3,
    "never again": 3,
    "disappointed": 3,

    # Level 2 — Flag
    "unhappy": 2,
    "frustrated": 2,
    "not working": 2,
    "broken": 2,
    "wrong": 2,
    "mistake": 2,
    "delay": 2,
    "late": 2,

    # Level 1 — Monitor
    "question": 1,
    "help": 1,
    "how to": 1,
    "confused": 1,
}


def evaluate_escalation(
    message: str,
    customer_tier: str = "standard",
    custom_keywords: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Evaluate whether a customer message requires escalation.

    Args:
        message: Customer message text.
        customer_tier: Customer tier (enterprise customers get higher priority).
        custom_keywords: Optional dict of keyword -> escalation level overrides.

    Returns:
        Dict with keys: level, level_name, triggers, recommendation.
    """
    keywords = {**DEFAULT_ESCALATION_KEYWORDS, **(custom_keywords or {})}
    message_lower = message.lower()

    triggered = {}
    max_level = 0

    for keyword, level in keywords.items():
        if keyword in message_lower:
            triggered[keyword] = level
            if level > max_level:
                max_level = level

    # Enterprise customers: bump level by 1 (max 4)
    if customer_tier == "enterprise" and max_level > 0:
        max_level = min(max_level + 1, 4)
    elif customer_tier == "premium" and max_level >= 3:
        max_level = min(max_level + 1, 4)

    level_name = ESCALATION_LEVELS.get(max_level, "none")

    recommendations = {
        0: "No escalation needed. Standard AI reply is appropriate.",
        1: "Monitor this conversation. AI reply is fine but flag for review.",
        2: "Flag for human review after AI reply is sent.",
        3: "Escalate to human agent before sending any reply.",
        4: "URGENT: Escalate immediately to senior team. Do not send AI reply.",
    }

    return {
        "level": max_level,
        "level_name": level_name,
        "triggers": triggered,
        "recommendation": recommendations.get(max_level, ""),
        "requires_human": max_level >= 3,
    }


def should_block_ai_reply(escalation_result: dict[str, Any]) -> bool:
    """Return True if AI should not send a reply (human must handle)."""
    return escalation_result.get("requires_human", False)
