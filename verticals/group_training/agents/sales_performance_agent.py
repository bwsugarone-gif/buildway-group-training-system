"""Rule-based sales performance analysis for group training agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from verticals.group_training.models import DailyActivityLog


@dataclass(frozen=True)
class SalesPerformanceAnalysis:
    agent_id: str
    performance_score: int
    strength_key: str
    weakness_key: str
    conversion_problem_stage: str
    explanation_key: str
    metrics: dict[str, float]


def analyze_sales_performance(logs: list[DailyActivityLog], today: date | None = None) -> SalesPerformanceAnalysis:
    today = today or date.today()
    agent_id = logs[0].agent_id if logs else ""
    last_7 = [log for log in logs if 0 <= (today - log.activity_date).days <= 6]
    last_30 = [log for log in logs if 0 <= (today - log.activity_date).days <= 29]
    sample = last_30 or logs

    calls = sum(log.call_count for log in sample)
    whatsapp = sum(log.whatsapp_count for log in sample)
    appointments = sum(log.appointment_count for log in sample)
    meetings = sum(log.meeting_count for log in sample)
    closings = sum(log.closing_count for log in sample)
    outreach = calls + whatsapp
    appointment_rate = appointments / outreach if outreach else 0.0
    meeting_rate = meetings / appointments if appointments else 0.0
    closing_rate = closings / meetings if meetings else 0.0
    active_days_7 = len({log.activity_date for log in last_7 if log.call_count + log.whatsapp_count > 0})
    stability = active_days_7 / 7

    score = round(
        min(outreach, 300) / 300 * 25
        + min(appointment_rate, 0.20) / 0.20 * 25
        + min(meeting_rate, 0.75) / 0.75 * 20
        + min(closing_rate, 0.40) / 0.40 * 20
        + stability * 10
    )
    score = max(0, min(100, score))

    if outreach < 20:
        stage = "activity_gap"
        weakness_key = "sales.weakness.activity_gap"
        explanation_key = "sales.explanation.activity_gap"
    elif appointment_rate < 0.08:
        stage = "appointment_conversion"
        weakness_key = "sales.weakness.appointment_conversion"
        explanation_key = "sales.explanation.appointment_conversion"
    elif appointments >= 3 and meeting_rate < 0.45:
        stage = "meeting_conversion"
        weakness_key = "sales.weakness.meeting_conversion"
        explanation_key = "sales.explanation.meeting_conversion"
    elif meetings >= 2 and closing_rate < 0.15:
        stage = "closing_conversion"
        weakness_key = "sales.weakness.closing_conversion"
        explanation_key = "sales.explanation.closing_conversion"
    else:
        stage = "balanced_pipeline"
        weakness_key = "sales.weakness.balanced_pipeline"
        explanation_key = "sales.explanation.balanced_pipeline"

    if closing_rate >= 0.25:
        strength_key = "sales.strength.closing"
    elif meeting_rate >= 0.55:
        strength_key = "sales.strength.meetings"
    elif appointment_rate >= 0.12:
        strength_key = "sales.strength.appointments"
    elif outreach >= 80:
        strength_key = "sales.strength.outreach"
    else:
        strength_key = "sales.strength.needs_pipeline"

    return SalesPerformanceAnalysis(
        agent_id=agent_id,
        performance_score=score,
        strength_key=strength_key,
        weakness_key=weakness_key,
        conversion_problem_stage=stage,
        explanation_key=explanation_key,
        metrics={
            "calls": calls,
            "whatsapp": whatsapp,
            "appointments": appointments,
            "meetings": meetings,
            "closings": closings,
            "appointment_rate": round(appointment_rate * 100, 1),
            "meeting_rate": round(meeting_rate * 100, 1),
            "closing_rate": round(closing_rate * 100, 1),
            "active_days_7": active_days_7,
        },
    )
