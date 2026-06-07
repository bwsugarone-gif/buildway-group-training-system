"""Team-level manager insight generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections import Counter

from verticals.group_training.agents.coaching_agent import CoachingPlan, build_coaching_plan
from verticals.group_training.agents.customer_opportunity_agent import CustomerOpportunityAnalysis, rank_customer_opportunities
from verticals.group_training.agents.sales_performance_agent import SalesPerformanceAnalysis
from verticals.group_training.models import ClosingScore, Customer, User


@dataclass(frozen=True)
class ManagerInsight:
    top_customers: list[CustomerOpportunityAnalysis]
    high_risk_agents: list[str]
    coaching_plans: list[CoachingPlan]
    team_problem_key: str
    manager_recommendation_key: str
    team_next_action_key: str
    summary_key: str
    affected_agent_count: int
    insight_reason_key: str
    supporting_metrics: dict[str, float]
    ai_confidence: int


def _empty_performance(agent_id: str) -> SalesPerformanceAnalysis:
    return SalesPerformanceAnalysis(
        agent_id=agent_id,
        performance_score=0,
        strength_key="",
        weakness_key="",
        conversion_problem_stage="activity_gap",
        explanation_key="",
        metrics={},
        team_average_comparison={},
        performance_gap={},
        trend_analysis={"direction": "stable", "window_days": 7, "recent_activity": 0, "previous_activity": 0},
    )


def build_manager_insight(
    agents: list[User],
    customers: list[Customer],
    opportunities: list[CustomerOpportunityAnalysis],
    performances: list[SalesPerformanceAnalysis],
    scores: list[ClosingScore],
    today: date | None = None,
) -> ManagerInsight:
    today = today or date.today()
    latest_scores: dict[str, ClosingScore] = {}
    for score in sorted(scores, key=lambda item: (item.score_date, item.created_at), reverse=True):
        latest_scores.setdefault(score.agent_id, score)

    performance_by_agent = {performance.agent_id: performance for performance in performances}
    coaching_plans = [
        build_coaching_plan(
            performance_by_agent.get(agent.id, _empty_performance(agent.id)),
            latest_scores.get(agent.id).hidden_score if agent.id in latest_scores else None,
            today,
        )
        for agent in agents
    ]
    high_risk_agents = [
        plan.agent_id
        for plan in coaching_plans
        if plan.risk_level in {"High", "Critical"}
    ][:5]
    problem_counts = Counter(performance.conversion_problem_stage for performance in performances)
    main_problem = problem_counts.most_common(1)[0][0] if problem_counts else "activity_gap"
    total_agents = len(agents)
    affected_count = problem_counts.get(main_problem, 0)
    confidence = min(95, 50 + min(total_agents, 20) + min(len(opportunities), 25))

    return ManagerInsight(
        top_customers=rank_customer_opportunities(opportunities)[:10],
        high_risk_agents=high_risk_agents,
        coaching_plans=sorted(coaching_plans, key=lambda plan: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(plan.risk_level, 9))[:5],
        team_problem_key=f"manager_insight.problem.{main_problem}",
        manager_recommendation_key=f"manager_insight.recommendation.{main_problem}",
        team_next_action_key=f"manager_insight.next_action.{main_problem}",
        summary_key="manager_insight.summary",
        affected_agent_count=affected_count,
        insight_reason_key=f"manager_insight.reason.{main_problem}",
        supporting_metrics={
            "total_agents": total_agents,
            "affected_agent_count": affected_count,
            "high_risk_agent_count": len(high_risk_agents),
            "top_customer_count": min(len(opportunities), 10),
        },
        ai_confidence=confidence,
    )
