"""In-memory repository for Phase 1 group training MVP."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import (
    AITrainingReview,
    ClosingScore,
    Customer,
    CustomerFollowup,
    DailyActivityLog,
    Team,
    User,
    UserRole,
)


class GroupTrainingRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.teams: dict[str, Team] = {}
        self.customers: dict[str, Customer] = {}
        self.followups: dict[str, CustomerFollowup] = {}
        self.daily_logs: dict[str, DailyActivityLog] = {}
        self.reviews: dict[str, AITrainingReview] = {}
        self.closing_scores: dict[str, ClosingScore] = {}

    def add_user(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def add_team(self, team: Team) -> Team:
        self.teams[team.id] = team
        return team

    def add_customer(self, customer: Customer) -> Customer:
        self.customers[customer.id] = customer
        return customer

    def add_followup(self, followup: CustomerFollowup) -> CustomerFollowup:
        self.followups[followup.id] = followup
        return followup

    def add_daily_log(self, log: DailyActivityLog) -> DailyActivityLog:
        self.daily_logs[log.id] = log
        return log

    def add_review(self, review: AITrainingReview) -> AITrainingReview:
        self.reviews[review.id] = review
        return review

    def add_closing_score(self, score: ClosingScore) -> ClosingScore:
        self.closing_scores[score.id] = score
        return score

    def list_users(self, tenant_id: str) -> list[User]:
        return [user for user in self.users.values() if user.tenant_id == tenant_id]

    def get_user(self, tenant_id: str, user_id: str) -> User | None:
        user = self.users.get(user_id)
        return user if user and user.tenant_id == tenant_id else None

    def find_user_by_email(self, tenant_id: str, email: str) -> User | None:
        normalized_email = email.strip().lower()
        for user in self.users.values():
            if user.tenant_id == tenant_id and user.email.lower() == normalized_email:
                return user
        return None

    def get_customer(self, tenant_id: str, customer_id: str) -> Customer | None:
        customer = self.customers.get(customer_id)
        return customer if customer and customer.tenant_id == tenant_id else None

    def list_agents_for_manager(self, tenant_id: str, manager_id: str) -> list[User]:
        return [
            user
            for user in self.users.values()
            if user.tenant_id == tenant_id
            and user.role == UserRole.AGENT
            and user.manager_id == manager_id
        ]

    def list_customers(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        team_id: str | None = None,
    ) -> list[Customer]:
        rows = [c for c in self.customers.values() if c.tenant_id == tenant_id]
        if agent_id:
            rows = [c for c in rows if c.agent_id == agent_id]
        if team_id:
            rows = [c for c in rows if c.team_id == team_id]
        return sorted(rows, key=lambda c: c.created_at, reverse=True)

    def list_followups(self, tenant_id: str, customer_id: str | None = None) -> list[CustomerFollowup]:
        rows = [f for f in self.followups.values() if f.tenant_id == tenant_id]
        if customer_id:
            rows = [f for f in rows if f.customer_id == customer_id]
        return sorted(rows, key=lambda f: f.created_at, reverse=True)

    def list_logs(
        self,
        tenant_id: str,
        activity_date: date | None = None,
        agent_id: str | None = None,
        team_id: str | None = None,
    ) -> list[DailyActivityLog]:
        rows = [l for l in self.daily_logs.values() if l.tenant_id == tenant_id]
        if activity_date:
            rows = [l for l in rows if l.activity_date == activity_date]
        if agent_id:
            rows = [l for l in rows if l.agent_id == agent_id]
        if team_id:
            rows = [l for l in rows if l.team_id == team_id]
        return sorted(rows, key=lambda l: (l.activity_date, l.created_at), reverse=True)

    def list_reviews(self, tenant_id: str, agent_id: str | None = None) -> list[AITrainingReview]:
        rows = [r for r in self.reviews.values() if r.tenant_id == tenant_id]
        if agent_id:
            rows = [r for r in rows if r.agent_id == agent_id]
        return sorted(rows, key=lambda r: r.created_at, reverse=True)

    def list_closing_scores(self, tenant_id: str, agent_id: str | None = None) -> list[ClosingScore]:
        rows = [s for s in self.closing_scores.values() if s.tenant_id == tenant_id]
        if agent_id:
            rows = [s for s in rows if s.agent_id == agent_id]
        return sorted(rows, key=lambda s: s.created_at, reverse=True)


def build_in_memory_repository() -> GroupTrainingRepository:
    tenant_id = "tenant_buildway_demo"
    repo = GroupTrainingRepository()
    repo.add_user(User(tenant_id, "admin_001", "Admin Demo", "admin@buildway.demo", UserRole.ADMIN))
    repo.add_user(User(tenant_id, "mgr_001", "Manager Demo", "manager@buildway.demo", UserRole.MANAGER, "team_alpha"))
    repo.add_user(User(tenant_id, "agt_001", "Agent A", "agent@buildway.demo", UserRole.AGENT, "team_alpha", "mgr_001"))
    repo.add_user(User(tenant_id, "agt_002", "Agent B", "agent.b@buildway.demo", UserRole.AGENT, "team_alpha", "mgr_001"))
    repo.add_team(Team(tenant_id, "team_alpha", "Alpha Insurance Team", "mgr_001"))
    return repo
