"""Agent-facing sales coaching helpers."""

from __future__ import annotations

from verticals.group_training.models import AITrainingReview


def agent_visible_feedback(review: AITrainingReview) -> dict[str, str]:
    return {
        "summary": review.summary,
        "improvement_advice": review.improvement_advice,
        "risk_level": review.risk_level,
    }

