"""Manager dashboard intelligence helpers."""

from __future__ import annotations

from verticals.group_training.models import AITrainingReview


def identify_high_risk_agents(reviews: list[AITrainingReview]) -> list[str]:
    latest_by_agent: dict[str, AITrainingReview] = {}
    for review in reviews:
        current = latest_by_agent.get(review.agent_id)
        if current is None or review.created_at > current.created_at:
            latest_by_agent[review.agent_id] = review
    return [review.agent_id for review in latest_by_agent.values() if review.risk_level == "High"]

