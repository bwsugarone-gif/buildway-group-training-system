"""Manager/Admin dashboard service for the group training vertical."""

from __future__ import annotations

from datetime import date

from verticals.group_training.agents.closing_agent import calculate_hidden_closing_score
from verticals.group_training.agents.manager_agent import identify_high_risk_agents
from verticals.group_training.agents.training_agent import review_daily_performance
from verticals.group_training.models import UserRole
from verticals.group_training.services.repository import GroupTrainingRepository


class DashboardService:
    def __init__(self, repo: GroupTrainingRepository) -> None:
        self.repo = repo

    def generate_reviews_for_date(self, tenant_id: str, activity_date: date) -> None:
        for log in self.repo.list_logs(tenant_id, activity_date=activity_date):
            self.repo.add_review(review_daily_performance(log))
            self.repo.add_closing_score(calculate_hidden_closing_score(log))

    def manager_dashboard(self, tenant_id: str, manager_id: str, viewer_role: UserRole) -> dict:
        manager = self.repo.get_user(tenant_id, manager_id)
        if not manager and viewer_role != UserRole.ADMIN:
            raise ValueError("manager not found for tenant")
        agents = self.repo.list_agents_for_manager(tenant_id, manager_id)
        agent_ids = {agent.id for agent in agents}
        team_ids = {agent.team_id for agent in agents if agent.team_id}
        logs = [log for team_id in team_ids for log in self.repo.list_logs(tenant_id, team_id=team_id)]
        reviews = [review for review in self.repo.list_reviews(tenant_id) if review.agent_id in agent_ids]
        dashboard = {
            "agents": agents,
            "daily_logs": logs,
            "reviews": reviews,
            "high_risk_agent_ids": identify_high_risk_agents(reviews),
        }
        if viewer_role in {UserRole.MANAGER, UserRole.ADMIN}:
            dashboard["closing_scores"] = [
                score for score in self.repo.list_closing_scores(tenant_id) if score.agent_id in agent_ids
            ]
        else:
            dashboard["closing_scores"] = []
        return dashboard

