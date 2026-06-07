"""Hidden closing score calculation for Manager/Admin visibility only."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import ClosingScore, DailyActivityLog


def hidden_score_breakdown(log: DailyActivityLog) -> dict[str, int]:
    activity_score = 15 if log.call_count + log.whatsapp_count >= 10 else 5
    appointment_score = min(log.appointment_count * 4, 16)
    meeting_score = min(log.meeting_count * 8, 24)
    closing_score = min(log.closing_count * 18, 30)
    discipline_score = 15
    if log.call_count + log.whatsapp_count < 10:
        discipline_score -= 10
    if log.meeting_count > 0 and log.closing_count == 0:
        discipline_score -= 5
    return {
        "activity_score": max(0, activity_score),
        "appointment_score": appointment_score,
        "meeting_score": meeting_score,
        "closing_score": closing_score,
        "discipline_score": max(0, discipline_score),
    }


def hidden_score_risk_level(hidden_score: int | float) -> str:
    if hidden_score >= 80:
        return "Low"
    if hidden_score >= 60:
        return "Medium"
    if hidden_score >= 40:
        return "High"
    return "Critical"


def calculate_hidden_closing_score(log: DailyActivityLog) -> ClosingScore:
    breakdown = hidden_score_breakdown(log)
    score = sum(breakdown.values())
    return ClosingScore(
        tenant_id=log.tenant_id,
        team_id=log.team_id,
        agent_id=log.agent_id,
        score_date=log.activity_date or date.today(),
        hidden_score=max(0, min(100, score)),
        rationale=(
            "Score = activity_score + appointment_score + meeting_score + "
            "closing_score + discipline_score."
        ),
    )
