"""Deterministic AI training review logic for Phase 1."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import AITrainingReview, DailyActivityLog


def review_daily_performance(log: DailyActivityLog) -> AITrainingReview:
    activity = log.call_count + log.whatsapp_count
    conversion_signal = log.appointment_count + log.meeting_count + (log.closing_count * 3)
    if activity < 10 and conversion_signal < 3:
        risk_level = "High"
        advice = "Increase prospecting volume and set a clear daily appointment target."
    elif log.meeting_count == 0:
        risk_level = "Medium"
        advice = "Improve call-to-appointment conversion and confirm meetings earlier in the day."
    elif log.closing_count == 0 and log.meeting_count >= 2:
        risk_level = "Medium"
        advice = "Strengthen proposal framing and rehearse objection handling before meetings."
    else:
        risk_level = "Low"
        advice = "Keep the current rhythm and document repeatable closing patterns."
    summary = (
        f"Activity: {activity} outreach touches, {log.appointment_count} appointments, "
        f"{log.meeting_count} meetings, {log.closing_count} closings."
    )
    return AITrainingReview(
        tenant_id=log.tenant_id,
        team_id=log.team_id,
        agent_id=log.agent_id,
        review_date=log.activity_date or date.today(),
        summary=summary,
        improvement_advice=advice,
        manager_feedback="Review pipeline quality, recent customer notes, and next-step discipline.",
        risk_level=risk_level,
    )

