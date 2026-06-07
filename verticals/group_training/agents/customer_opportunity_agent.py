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
    score_breakdown: dict[str, int]
    score_reason_key: str
    confidence: int


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
    stage_score = STAGE_BASE_SCORE.get(customer.stage, 30)
    meeting_score = _meeting_timing_score(customer, today)
    notes_score = _notes_signal_score(customer)
    followup_score = 5 if followups else 0
    agent_activity_score = _agent_activity_score(customer, agent_logs, today)
    raw_score = stage_score + meeting_score + notes_score + followup_score + agent_activity_score
    score = max(0, min(100, raw_score))

    if score >= 75:
        priority = "High"
    elif score >= 45:
        priority = "Medium"
    else:
        priority = "Low"

    reason_key, action_key, message_key = _stage_keys(customer.stage)
    deadline = _followup_deadline(customer, priority, today)
    contact_method_key = "opportunity.contact.call" if priority == "High" else "opportunity.contact.whatsapp"

    evidence_points = 1
    evidence_points += 1 if customer.next_meeting_date else 0
    evidence_points += 1 if customer.notes else 0
    evidence_points += 1 if followups else 0
    evidence_points += 1 if agent_logs else 0
    confidence = min(95, 45 + evidence_points * 10)

    return CustomerOpportunityAnalysis(
        customer_id=customer.id,
        opportunity_score=score,
        priority=priority,
        reason_key=reason_key,
        next_best_action_key=action_key,
        suggested_message_key=message_key,
        contact_method_key=contact_method_key,
        followup_deadline=deadline,
        score_breakdown={
            "stage_score": stage_score,
            "meeting_timing_score": meeting_score,
            "notes_signal_score": notes_score,
            "followup_history_score": followup_score,
            "agent_activity_score": agent_activity_score,
        },
        score_reason_key="opportunity.score_reason",
        confidence=confidence,
    )


def rank_customer_opportunities(analyses: list[CustomerOpportunityAnalysis]) -> list[CustomerOpportunityAnalysis]:
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(analyses, key=lambda item: (priority_rank.get(item.priority, 9), -item.opportunity_score, item.followup_deadline))


def _meeting_timing_score(customer: Customer, today: date) -> int:
    if customer.next_meeting_date == today:
        return 15
    if customer.next_meeting_date and 0 < (customer.next_meeting_date - today).days <= 3:
        return 12
    if customer.next_meeting_date and customer.next_meeting_date < today and customer.stage not in {CustomerStage.CLOSED, CustomerStage.LOST}:
        return 8
    return 0


def _notes_signal_score(customer: Customer) -> int:
    notes = (customer.notes or "").lower()
    keywords = ["保障", "方案", "成交", "proposal", "closing", "high potential"]
    return 8 if any(keyword in notes for keyword in keywords) else 0


def _agent_activity_score(customer: Customer, agent_logs: list[DailyActivityLog], today: date) -> int:
    recent_activity = sum(
        log.call_count + log.whatsapp_count + (log.appointment_count * 3) + (log.meeting_count * 5)
        for log in agent_logs
        if 0 <= (today - log.activity_date).days <= 7
    )
    if recent_activity >= 80:
        return 5
    if recent_activity < 20 and customer.stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}:
        return -8
    return 0


def _stage_keys(stage: CustomerStage) -> tuple[str, str, str]:
    if stage == CustomerStage.PROPOSAL:
        return "opportunity.reason.proposal", "opportunity.action.proposal", "opportunity.message.proposal"
    if stage == CustomerStage.HOT:
        return "opportunity.reason.hot", "opportunity.action.hot", "opportunity.message.hot"
    if stage == CustomerStage.WARM:
        return "opportunity.reason.warm", "opportunity.action.warm", "opportunity.message.warm"
    if stage == CustomerStage.CLOSED:
        return "opportunity.reason.closed", "opportunity.action.closed", "opportunity.message.closed"
    if stage == CustomerStage.LOST:
        return "opportunity.reason.lost", "opportunity.action.lost", "opportunity.message.lost"
    return "opportunity.reason.cold", "opportunity.action.cold", "opportunity.message.cold"


def _followup_deadline(customer: Customer, priority: str, today: date) -> date:
    if customer.next_meeting_date and customer.next_meeting_date >= today:
        return min(customer.next_meeting_date, today + timedelta(days=3 if priority == "High" else 7))
    if priority == "High":
        return today + timedelta(days=1)
    if priority == "Medium":
        return today + timedelta(days=3)
    return today + timedelta(days=14)
