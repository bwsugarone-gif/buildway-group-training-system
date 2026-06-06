"""Deterministic demo dataset and dashboard helpers for the Streamlit demo."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

from verticals.group_training.agents.closing_agent import calculate_hidden_closing_score
from verticals.group_training.agents.training_agent import review_daily_performance
from verticals.group_training.models import Customer, CustomerFollowup, CustomerStage, DailyActivityLog, User, UserRole
from verticals.group_training.services.auth_service import hash_password


DEMO_AGENT_PREFIX = "agt_demo_"
DEMO_CUSTOMER_PREFIX = "cust_demo_"
DEMO_FOLLOWUP_PREFIX = "follow_demo_"
DEMO_LOG_PREFIX = "log_demo_"
DEMO_REVIEW_PREFIX = "review_demo_"
DEMO_SCORE_PREFIX = "score_demo_"
DEMO_AGENT_COUNT = 20
DEMO_CUSTOMER_COUNT = 200
DEMO_LOG_DAYS = 25


def demo_dataset_allowed(tenant_id: str) -> bool:
    return tenant_id == "tenant_buildway_demo" or os.environ.get("BUILDWAY_GROUP_TRAINING_CLOUD_DEMO", "").lower() in {
        "1",
        "true",
        "yes",
    }


def reset_demo_dataset(repo: Any, tenant_id: str) -> None:
    """Remove only deterministic demo records, leaving manual tenant data intact."""
    if hasattr(repo, "_connect"):
        with repo._connect() as conn:
            conn.execute(
                "DELETE FROM closing_scores WHERE tenant_id = ? AND (id LIKE ? OR agent_id LIKE ?)",
                (tenant_id, f"{DEMO_SCORE_PREFIX}%", f"{DEMO_AGENT_PREFIX}%"),
            )
            conn.execute(
                "DELETE FROM ai_training_reviews WHERE tenant_id = ? AND (id LIKE ? OR agent_id LIKE ?)",
                (tenant_id, f"{DEMO_REVIEW_PREFIX}%", f"{DEMO_AGENT_PREFIX}%"),
            )
            conn.execute(
                "DELETE FROM daily_activity_logs WHERE tenant_id = ? AND (id LIKE ? OR agent_id LIKE ?)",
                (tenant_id, f"{DEMO_LOG_PREFIX}%", f"{DEMO_AGENT_PREFIX}%"),
            )
            conn.execute(
                "DELETE FROM customer_followups WHERE tenant_id = ? AND (id LIKE ? OR agent_id LIKE ?)",
                (tenant_id, f"{DEMO_FOLLOWUP_PREFIX}%", f"{DEMO_AGENT_PREFIX}%"),
            )
            conn.execute(
                "DELETE FROM customers WHERE tenant_id = ? AND (id LIKE ? OR agent_id LIKE ?)",
                (tenant_id, f"{DEMO_CUSTOMER_PREFIX}%", f"{DEMO_AGENT_PREFIX}%"),
            )
            conn.execute(
                "DELETE FROM users WHERE tenant_id = ? AND id LIKE ?",
                (tenant_id, f"{DEMO_AGENT_PREFIX}%"),
            )
        return

    for table_name, prefixes in {
        "closing_scores": (DEMO_SCORE_PREFIX, DEMO_AGENT_PREFIX),
        "reviews": (DEMO_REVIEW_PREFIX, DEMO_AGENT_PREFIX),
        "daily_logs": (DEMO_LOG_PREFIX, DEMO_AGENT_PREFIX),
        "followups": (DEMO_FOLLOWUP_PREFIX, DEMO_AGENT_PREFIX),
        "customers": (DEMO_CUSTOMER_PREFIX, DEMO_AGENT_PREFIX),
        "users": (DEMO_AGENT_PREFIX,),
    }.items():
        table = getattr(repo, table_name)
        for row_id, row in list(table.items()):
            agent_id = getattr(row, "agent_id", "")
            if row.tenant_id == tenant_id and (row_id.startswith(prefixes[0]) or agent_id.startswith(DEMO_AGENT_PREFIX)):
                del table[row_id]


def seed_demo_dataset(repo: Any, tenant_id: str, team_id: str, manager_id: str) -> dict[str, int]:
    if not demo_dataset_allowed(tenant_id):
        return {"agents": 0, "customers": 0, "daily_logs": 0, "reviews": 0, "closing_scores": 0}
    reset_demo_dataset(repo, tenant_id)
    today = date.today()
    now = datetime.utcnow()

    agents = []
    for index in range(1, DEMO_AGENT_COUNT + 1):
        agent = User(
            tenant_id=tenant_id,
            id=f"{DEMO_AGENT_PREFIX}{index:03d}",
            name=f"Demo Agent {index:02d}",
            email=f"demo.agent{index:02d}@buildway.demo",
            role=UserRole.AGENT,
            team_id=team_id,
            manager_id=manager_id,
            password_hash=hash_password("Demo123!"),
        )
        repo.add_user(agent)
        agents.append(agent)

    stages = [
        CustomerStage.COLD,
        CustomerStage.WARM,
        CustomerStage.HOT,
        CustomerStage.PROPOSAL,
        CustomerStage.CLOSED,
        CustomerStage.LOST,
    ]
    stage_weights = [42, 58, 36, 28, 22, 14]
    weighted_stages = [stage for stage, count in zip(stages, stage_weights) for _ in range(count)]
    for index in range(1, DEMO_CUSTOMER_COUNT + 1):
        agent = agents[(index - 1) % len(agents)]
        stage = weighted_stages[(index - 1) % len(weighted_stages)]
        if index % 13 == 0:
            next_meeting = today - timedelta(days=(index % 5) + 1)
        elif index % 9 == 0:
            next_meeting = today
        else:
            next_meeting = today + timedelta(days=index % 14)
        customer = Customer(
            tenant_id=tenant_id,
            team_id=team_id,
            agent_id=agent.id,
            name=f"Demo Customer {index:03d}",
            stage=stage,
            phone=f"6{index:07d}",
            notes=_customer_note(stage, index),
            next_meeting_date=next_meeting,
            id=f"{DEMO_CUSTOMER_PREFIX}{index:03d}",
            created_at=now - timedelta(days=index % 30, minutes=index),
        )
        repo.add_customer(customer)
        if index <= 90:
            repo.add_followup(
                CustomerFollowup(
                    tenant_id=tenant_id,
                    customer_id=customer.id,
                    agent_id=agent.id,
                    note=_followup_note(stage, index),
                    next_action=_next_action(stage, next_meeting),
                    id=f"{DEMO_FOLLOWUP_PREFIX}{index:03d}",
                    created_at=now - timedelta(days=index % 12, minutes=index),
                )
            )

    for agent_index, agent in enumerate(agents, start=1):
        for day_offset in range(DEMO_LOG_DAYS):
            log_date = today - timedelta(days=day_offset)
            call_count, whatsapp_count, appointments, meetings, closings = _activity_counts(agent_index, day_offset)
            log = DailyActivityLog(
                tenant_id=tenant_id,
                team_id=team_id,
                agent_id=agent.id,
                activity_date=log_date,
                call_count=call_count,
                whatsapp_count=whatsapp_count,
                appointment_count=appointments,
                meeting_count=meetings,
                closing_count=closings,
                notes=_log_note(agent_index, day_offset),
                id=f"{DEMO_LOG_PREFIX}{agent_index:03d}_{day_offset:02d}",
                created_at=now - timedelta(days=day_offset, minutes=agent_index),
            )
            repo.add_daily_log(log)
            review = review_daily_performance(log)
            review.id = f"{DEMO_REVIEW_PREFIX}{agent_index:03d}_{day_offset:02d}"
            review.created_at = log.created_at
            repo.add_review(review)
            score = calculate_hidden_closing_score(log)
            score.id = f"{DEMO_SCORE_PREFIX}{agent_index:03d}_{day_offset:02d}"
            score.created_at = log.created_at
            repo.add_closing_score(score)

    return {
        "agents": DEMO_AGENT_COUNT,
        "customers": DEMO_CUSTOMER_COUNT,
        "daily_logs": DEMO_AGENT_COUNT * DEMO_LOG_DAYS,
        "reviews": DEMO_AGENT_COUNT * DEMO_LOG_DAYS,
        "closing_scores": DEMO_AGENT_COUNT * DEMO_LOG_DAYS,
    }


def generate_demo_dashboard_metrics(agents, customers, logs, reviews, scores) -> dict[str, Any]:
    today = date.today()
    week_end = today + timedelta(days=7)
    latest_logs = _latest_logs_by_agent(logs)
    latest_scores = _latest_scores_by_agent(scores)
    high_potential = [customer for customer in customers if customer.stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}]
    overdue = [
        customer
        for customer in customers
        if customer.next_meeting_date and customer.next_meeting_date < today and customer.stage not in {CustomerStage.CLOSED, CustomerStage.LOST}
    ]
    weekly_followups = [
        customer for customer in customers if customer.next_meeting_date and today <= customer.next_meeting_date <= week_end
    ]
    today_logs = [log for log in logs if log.activity_date == today]
    low_active_agent_ids = {
        agent.id
        for agent in agents
        if sum(
            log.call_count + log.whatsapp_count
            for log in logs
            if log.agent_id == agent.id and (today - log.activity_date).days < 7
        )
        < 70
    }
    high_risk_agent_ids = {
        review.agent_id for review in _latest_reviews_by_agent(reviews).values() if review.risk_level == "High"
    } | low_active_agent_ids
    top_agents = sorted(
        (
            {
                "agent_id": agent.id,
                "activity_score": _agent_activity_score([log for log in latest_logs.values() if log.agent_id == agent.id]),
                "hidden_score": latest_scores.get(agent.id).hidden_score if agent.id in latest_scores else 0,
            }
            for agent in agents
        ),
        key=lambda row: (row["hidden_score"], row["activity_score"]),
        reverse=True,
    )[:5]
    hidden_average = round(sum(score.hidden_score for score in latest_scores.values()) / len(latest_scores), 1) if latest_scores else 0.0
    return {
        "team_total_customers": len(customers),
        "today_activity_count": sum(
            log.call_count + log.whatsapp_count + log.appointment_count + log.meeting_count + log.closing_count
            for log in today_logs
        ),
        "weekly_followup_count": len(weekly_followups),
        "overdue_followup_count": len(overdue),
        "high_potential_customer_count": len(high_potential),
        "low_active_agent_count": len(low_active_agent_ids),
        "hidden_score_average": hidden_average,
        "top_agents": top_agents,
        "risk_agent_ids": sorted(high_risk_agent_ids),
        "high_potential_customers": high_potential[:8],
        "followup_customers": sorted(overdue or weekly_followups, key=lambda c: c.next_meeting_date or today)[:8],
    }


def generate_demo_ai_insights(user, agents, customers, logs, reviews, scores) -> dict[str, Any]:
    visible_customers = customers if user.role != UserRole.AGENT else [customer for customer in customers if customer.agent_id == user.id]
    visible_logs = logs if user.role != UserRole.AGENT else [log for log in logs if log.agent_id == user.id]
    visible_reviews = reviews if user.role != UserRole.AGENT else [review for review in reviews if review.agent_id == user.id]
    metrics = generate_demo_dashboard_metrics(agents, visible_customers, visible_logs, visible_reviews, scores)
    today = date.today()
    today_logs = [log for log in visible_logs if log.activity_date == today]
    latest_review = next(iter(_latest_reviews_by_agent(visible_reviews).values()), None)
    return {
        "today_outreach": sum(log.call_count + log.whatsapp_count for log in today_logs),
        "today_meetings": sum(log.meeting_count for log in today_logs),
        "latest_risk": latest_review.risk_level if latest_review else "Low",
        "high_potential_customers": metrics["high_potential_customers"],
        "followup_customers": metrics["followup_customers"],
        "low_active_agent_count": metrics["low_active_agent_count"],
        "risk_agent_ids": metrics["risk_agent_ids"],
    }


def _customer_note(stage: CustomerStage, index: int) -> str:
    if stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}:
        return f"High potential case. Needs proposal follow-up #{index}."
    if stage == CustomerStage.WARM:
        return f"Warm prospect. Confirm needs and next meeting #{index}."
    if stage == CustomerStage.CLOSED:
        return f"Closed case. Prepare policy service follow-up #{index}."
    if stage == CustomerStage.LOST:
        return f"Lost case. Keep light-touch renewal contact #{index}."
    return f"Cold lead. Continue qualification #{index}."


def _followup_note(stage: CustomerStage, index: int) -> str:
    if stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}:
        return f"Reviewed needs and prepared proposal pack #{index}."
    if stage == CustomerStage.WARM:
        return f"Confirmed interest and arranged next discussion #{index}."
    return f"Completed routine follow-up #{index}."


def _next_action(stage: CustomerStage, next_meeting: date | None) -> str:
    if stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}:
        return f"Prepare closing conversation for {next_meeting.isoformat() if next_meeting else 'next meeting'}"
    if stage == CustomerStage.WARM:
        return f"Confirm appointment for {next_meeting.isoformat() if next_meeting else 'this week'}"
    return "Keep in monthly nurture list"


def _activity_counts(agent_index: int, day_offset: int) -> tuple[int, int, int, int, int]:
    if agent_index >= 17:
        calls = 3 + (day_offset % 4)
        whatsapp = 2 + (agent_index % 3)
        appointments = 0 if day_offset % 3 else 1
        meetings = 0 if day_offset % 4 else 1
        closings = 0
        return calls, whatsapp, appointments, meetings, closings
    calls = 14 + ((agent_index + day_offset) % 12)
    whatsapp = 8 + ((agent_index * 2 + day_offset) % 10)
    appointments = 1 + ((agent_index + day_offset) % 4)
    meetings = (agent_index + day_offset) % 3
    closings = 1 if (agent_index + day_offset) % 9 == 0 else 0
    return calls, whatsapp, appointments, meetings, closings


def _log_note(agent_index: int, day_offset: int) -> str:
    if agent_index >= 17:
        return "Low activity day. Needs manager coaching."
    if day_offset % 7 == 0:
        return "Strong pipeline follow-up and proposal preparation."
    return "Regular prospecting, appointments, and customer follow-up."


def _latest_logs_by_agent(logs) -> dict[str, DailyActivityLog]:
    latest: dict[str, DailyActivityLog] = {}
    for log in sorted(logs, key=lambda item: (item.activity_date, item.created_at), reverse=True):
        latest.setdefault(log.agent_id, log)
    return latest


def _latest_reviews_by_agent(reviews) -> dict[str, Any]:
    latest = {}
    for review in sorted(reviews, key=lambda item: (item.review_date, item.created_at), reverse=True):
        latest.setdefault(review.agent_id, review)
    return latest


def _latest_scores_by_agent(scores) -> dict[str, Any]:
    latest = {}
    for score in sorted(scores, key=lambda item: (item.score_date, item.created_at), reverse=True):
        latest.setdefault(score.agent_id, score)
    return latest


def _agent_activity_score(logs) -> int:
    return sum(
        log.call_count
        + log.whatsapp_count
        + (log.appointment_count * 4)
        + (log.meeting_count * 8)
        + (log.closing_count * 20)
        for log in logs
    )
