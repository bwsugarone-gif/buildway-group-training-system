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
    team_average_comparison: dict[str, float]
    performance_gap: dict[str, float]
    trend_analysis: dict[str, float | str]


def analyze_sales_performance(
    logs: list[DailyActivityLog],
    today: date | None = None,
    team_logs: list[DailyActivityLog] | None = None,
) -> SalesPerformanceAnalysis:
    today = today or date.today()
    agent_id = logs[0].agent_id if logs else ""
    metrics = _metrics_for_logs(logs, today)
    team_metrics = _team_average_metrics(team_logs or logs, today)
    gap = {
        key: round(metrics.get(key, 0.0) - team_metrics.get(key, 0.0), 1)
        for key in ["outreach", "appointment_rate", "meeting_rate", "closing_rate", "active_days_7"]
    }
    trend = _trend_analysis(logs, today)
    score = _performance_score(metrics)
    stage, weakness_key, explanation_key = _problem_stage(metrics)
    strength_key = _strength_key(metrics)

    return SalesPerformanceAnalysis(
        agent_id=agent_id,
        performance_score=score,
        strength_key=strength_key,
        weakness_key=weakness_key,
        conversion_problem_stage=stage,
        explanation_key=explanation_key,
        metrics=metrics,
        team_average_comparison=team_metrics,
        performance_gap=gap,
        trend_analysis=trend,
    )


def _metrics_for_logs(logs: list[DailyActivityLog], today: date) -> dict[str, float]:
    last_7 = [log for log in logs if 0 <= (today - log.activity_date).days <= 6]
    last_30 = [log for log in logs if 0 <= (today - log.activity_date).days <= 29]
    sample = last_30 or logs
    calls = sum(log.call_count for log in sample)
    whatsapp = sum(log.whatsapp_count for log in sample)
    appointments = sum(log.appointment_count for log in sample)
    meetings = sum(log.meeting_count for log in sample)
    closings = sum(log.closing_count for log in sample)
    outreach = calls + whatsapp
    appointment_rate = appointments / outreach * 100 if outreach else 0.0
    meeting_rate = meetings / appointments * 100 if appointments else 0.0
    closing_rate = closings / meetings * 100 if meetings else 0.0
    active_days_7 = len({log.activity_date for log in last_7 if log.call_count + log.whatsapp_count > 0})
    return {
        "calls": calls,
        "whatsapp": whatsapp,
        "appointments": appointments,
        "meetings": meetings,
        "closings": closings,
        "outreach": outreach,
        "appointment_rate": round(appointment_rate, 1),
        "meeting_rate": round(meeting_rate, 1),
        "closing_rate": round(closing_rate, 1),
        "active_days_7": active_days_7,
    }


def _team_average_metrics(team_logs: list[DailyActivityLog], today: date) -> dict[str, float]:
    agent_ids = sorted({log.agent_id for log in team_logs})
    if not agent_ids:
        return {"outreach": 0.0, "appointment_rate": 0.0, "meeting_rate": 0.0, "closing_rate": 0.0, "active_days_7": 0.0}
    rows = [_metrics_for_logs([log for log in team_logs if log.agent_id == agent_id], today) for agent_id in agent_ids]
    return {
        key: round(sum(row[key] for row in rows) / len(rows), 1)
        for key in ["outreach", "appointment_rate", "meeting_rate", "closing_rate", "active_days_7"]
    }


def _trend_analysis(logs: list[DailyActivityLog], today: date) -> dict[str, float | str]:
    current = [log for log in logs if 0 <= (today - log.activity_date).days <= 6]
    previous = [log for log in logs if 7 <= (today - log.activity_date).days <= 13]
    current_outreach = sum(log.call_count + log.whatsapp_count for log in current)
    previous_outreach = sum(log.call_count + log.whatsapp_count for log in previous)
    delta = current_outreach - previous_outreach
    if delta > 10:
        direction = "up"
    elif delta < -10:
        direction = "down"
    else:
        direction = "stable"
    return {
        "current_7_day_outreach": current_outreach,
        "previous_7_day_outreach": previous_outreach,
        "outreach_delta": delta,
        "direction": direction,
    }


def _performance_score(metrics: dict[str, float]) -> int:
    score = round(
        min(metrics["outreach"], 300) / 300 * 25
        + min(metrics["appointment_rate"], 20) / 20 * 25
        + min(metrics["meeting_rate"], 75) / 75 * 20
        + min(metrics["closing_rate"], 40) / 40 * 20
        + (metrics["active_days_7"] / 7) * 10
    )
    return max(0, min(100, score))


def _problem_stage(metrics: dict[str, float]) -> tuple[str, str, str]:
    if metrics["outreach"] < 20:
        return "activity_gap", "sales.weakness.activity_gap", "sales.explanation.activity_gap"
    if metrics["appointment_rate"] < 8:
        return "appointment_conversion", "sales.weakness.appointment_conversion", "sales.explanation.appointment_conversion"
    if metrics["appointments"] >= 3 and metrics["meeting_rate"] < 45:
        return "meeting_conversion", "sales.weakness.meeting_conversion", "sales.explanation.meeting_conversion"
    if metrics["meetings"] >= 2 and metrics["closing_rate"] < 15:
        return "closing_conversion", "sales.weakness.closing_conversion", "sales.explanation.closing_conversion"
    return "balanced_pipeline", "sales.weakness.balanced_pipeline", "sales.explanation.balanced_pipeline"


def _strength_key(metrics: dict[str, float]) -> str:
    if metrics["closing_rate"] >= 25:
        return "sales.strength.closing"
    if metrics["meeting_rate"] >= 55:
        return "sales.strength.meetings"
    if metrics["appointment_rate"] >= 12:
        return "sales.strength.appointments"
    if metrics["outreach"] >= 80:
        return "sales.strength.outreach"
    return "sales.strength.needs_pipeline"
