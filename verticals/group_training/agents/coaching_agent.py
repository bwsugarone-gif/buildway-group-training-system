"""Manager coaching plan generation for group training."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from verticals.group_training.agents.closing_agent import hidden_score_risk_level
from verticals.group_training.agents.sales_performance_agent import SalesPerformanceAnalysis


@dataclass(frozen=True)
class CoachingPlan:
    agent_id: str
    coaching_topic_key: str
    reason_key: str
    training_focus_key: str
    next_action_key: str
    manager_action_key: str
    target_metric_key: str
    target_deadline: date
    risk_level: str
    why_this_coaching_key: str
    target_metric: str
    target_date: date
    expected_improvement_key: str


def build_coaching_plan(
    performance: SalesPerformanceAnalysis,
    hidden_score: int | None,
    today: date | None = None,
) -> CoachingPlan:
    today = today or date.today()
    risk_level = hidden_score_risk_level(hidden_score if hidden_score is not None else performance.performance_score)
    stage = performance.conversion_problem_stage
    if risk_level == "Critical" and stage == "balanced_pipeline":
        stage = "activity_gap"

    return CoachingPlan(
        agent_id=performance.agent_id,
        coaching_topic_key=f"coaching.topic.{stage}",
        reason_key=f"coaching.reason.{stage}",
        training_focus_key=f"coaching.focus.{stage}",
        next_action_key=f"coaching.agent_next_action.{stage}",
        manager_action_key=f"coaching.manager_action.{stage}",
        target_metric_key=f"coaching.target_metric.{stage}",
        target_deadline=today + timedelta(days=7),
        risk_level=risk_level,
        why_this_coaching_key=f"coaching.why.{stage}",
        target_metric=_target_metric(stage),
        target_date=today + timedelta(days=7),
        expected_improvement_key=f"coaching.expected_improvement.{stage}",
    )


def _target_metric(stage: str) -> str:
    if stage == "activity_gap":
        return "20 outreach/day"
    if stage == "appointment_conversion":
        return "12% appointment rate"
    if stage == "meeting_conversion":
        return "60% meeting attendance"
    if stage == "closing_conversion":
        return "20% closing rate"
    return "Maintain current conversion"
