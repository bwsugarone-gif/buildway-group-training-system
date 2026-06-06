"""Daily activity log service."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import DailyActivityLog
from verticals.group_training.schemas import coerce_date, require_non_negative, require_tenant_id
from verticals.group_training.services.repository import GroupTrainingRepository


class DailyLogService:
    def __init__(self, repo: GroupTrainingRepository) -> None:
        self.repo = repo

    def create_log(
        self,
        tenant_id: str,
        team_id: str,
        agent_id: str,
        activity_date: date | None = None,
        call_count: int = 0,
        whatsapp_count: int = 0,
        appointment_count: int = 0,
        meeting_count: int = 0,
        closing_count: int = 0,
        notes: str = "",
    ) -> DailyActivityLog:
        require_tenant_id(tenant_id)
        log = DailyActivityLog(
            tenant_id=tenant_id,
            team_id=team_id,
            agent_id=agent_id,
            activity_date=coerce_date(activity_date),
            call_count=require_non_negative(call_count, "call_count"),
            whatsapp_count=require_non_negative(whatsapp_count, "whatsapp_count"),
            appointment_count=require_non_negative(appointment_count, "appointment_count"),
            meeting_count=require_non_negative(meeting_count, "meeting_count"),
            closing_count=require_non_negative(closing_count, "closing_count"),
            notes=notes.strip(),
        )
        return self.repo.add_daily_log(log)

