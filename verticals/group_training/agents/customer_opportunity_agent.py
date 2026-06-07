"""Customer opportunity scoring for group training CRM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from verticals.group_training.models import Customer, CustomerFollowup, CustomerStage, DailyActivityLog


@dataclass(frozen=True)
class CustomerOpportunityAnalysis:
    customer_id: str
    opportunity_score: int
    priority: str
    reason_key: str
    next_best_action_key: str
    suggested_message_key: str
    contact_method_key: str
    followup_deadline: date


STAGE_BASE_SCORE = {
    CustomerStage.COLD: 25,
    CustomerStage.WARM: 45,
    CustomerStage.HOT: 75,
    CustomerStage.PROPOSAL: 85,
    CustomerStage.CLOSED: 65,
    CustomerStage.LOST: 15,
}


def analyze_customer_opportunity(
    customer: Customer,
    followups: list[CustomerFollowup],
    agent_logs: list[DailyActivityLog],
    today: date | None = None,
) -> CustomerOpportunityAnalysis:
    today = today or date.today()
    score = STAGE_BASE_SCORE.get(customer.stage, 30)
    latest_followup = max(followups, key=lambda row: row.created_at, default=None)
    recent_activity = sum(
        log.call_count + log.whatsapp_count + (log.appointment_count * 3) + (log.meeting_count * 5)
        for log in agent_logs
        if 0 <= (today - log.activity_date).days <= 7
    )

    if customer.next_meeting_date == today:
        score += 15
    elif customer.next_meeting_date and 0 < (customer.next_meeting_date - today).days <= 3:
        score += 12
    elif customer.next_meeting_date and customer.next_meeting_date < today and customer.stage not in {CustomerStage.CLOSED, CustomerStage.LOST}:
        score += 8

    notes = (customer.notes or "").lower()
    if any(keyword in notes for keyword in ["保障", "方案", "成交", "proposal", "closing", "high potential"]):
        score += 8
    if latest_followup:
        score += 5
    if recent_activity >= 80:
        score += 5
    elif recent_activity < 20 and customer.stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}:
        score -= 8

    score = max(0, min(100, score))
    if score >= 75:
        priority = "High"
    elif score >= 45:
        priority = "Medium"
    else:
        priority = "Low"

    if customer.stage == CustomerStage.PROPOSAL:
        reason_key = "opportunity.reason.proposal"
        action_key = "opportunity.action.proposal"
        message_key = "opportunity.message.proposal"
    elif customer.stage == CustomerStage.HOT:
        reason_key = "opportunity.reason.hot"
        action_key = "opportunity.action.hot"
        message_key = "opportunity.message.hot"
    elif customer.stage == CustomerStage.WARM:
        reason_key = "opportunity.reason.warm"
        action_key = "opportunity.action.warm"
        message_key = "opportunity.message.warm"
    elif customer.stage == CustomerStage.CLOSED:
        reason_key = "opportunity.reason.closed"
        action_key = "opportunity.action.closed"
        message_key = "opportunity.message.closed"
    elif customer.stage == CustomerStage.LOST:
        reason_key = "opportunity.reason.lost"
        action_key = "opportunity.action.lost"
        message_key = "opportunity.message.lost"
    else:
        reason_key = "opportunity.reason.cold"
        action_key = "opportunity.action.cold"
        message_key = "opportunity.message.cold"

    if customer.next_meeting_date and customer.next_meeting_date >= today:
        deadline = min(customer.next_meeting_date, today + timedelta(days=3 if priority == "High" else 7))
    elif priority == "High":
        deadline = today + timedelta(days=1)
    elif priority == "Medium":
        deadline = today + timedelta(days=3)
    else:
        deadline = today + timedelta(days=14)

    contact_method_key = "opportunity.contact.call" if priority == "High" else "opportunity.contact.whatsapp"

    return CustomerOpportunityAnalysis(
        customer_id=customer.id,
        opportunity_score=score,
        priority=priority,
        reason_key=reason_key,
        next_best_action_key=action_key,
        suggested_message_key=message_key,
        contact_method_key=contact_method_key,
        followup_deadline=deadline,
    )


def rank_customer_opportunities(analyses: list[CustomerOpportunityAnalysis]) -> list[CustomerOpportunityAnalysis]:
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(analyses, key=lambda item: (priority_rank.get(item.priority, 9), -item.opportunity_score, item.followup_deadline))
