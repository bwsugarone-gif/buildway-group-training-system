"""Hidden closing score calculation for Manager/Admin visibility only."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import ClosingScore, DailyActivityLog


def calculate_hidden_closing_score(log: DailyActivityLog) -> ClosingScore:
    score = 45
    score += min(log.meeting_count * 8, 24)
    score += min(log.appointment_count * 4, 16)
    score += min(log.closing_count * 18, 30)
    if log.call_count + log.whatsapp_count < 10:
        score -= 10
    if log.meeting_count > 0 and log.closing_count == 0:
        score -= 5
    return ClosingScore(
        tenant_id=log.tenant_id,
        team_id=log.team_id,
        agent_id=log.agent_id,
        score_date=log.activity_date or date.today(),
        hidden_score=max(0, min(100, score)),
        rationale="Score blends outreach consistency, appointments, meetings, and closings.",
    )

