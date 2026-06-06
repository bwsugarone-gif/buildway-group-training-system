"""Customer CRM and RAM customer history services."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import Customer, CustomerFollowup
from verticals.group_training.schemas import parse_customer_stage, require_tenant_id
from verticals.group_training.services.repository import GroupTrainingRepository


class CustomerService:
    def __init__(self, repo: GroupTrainingRepository) -> None:
        self.repo = repo

    def create_customer(
        self,
        tenant_id: str,
        team_id: str,
        agent_id: str,
        name: str,
        stage: str,
        phone: str = "",
        notes: str = "",
        next_meeting_date: date | None = None,
    ) -> Customer:
        require_tenant_id(tenant_id)
        customer = Customer(
            tenant_id=tenant_id,
            team_id=team_id,
            agent_id=agent_id,
            name=name.strip(),
            stage=parse_customer_stage(stage),
            phone=phone.strip(),
            notes=notes.strip(),
            next_meeting_date=next_meeting_date,
        )
        if not customer.name:
            raise ValueError("customer name is required")
        return self.repo.add_customer(customer)

    def add_followup(
        self,
        tenant_id: str,
        customer_id: str,
        agent_id: str,
        note: str,
        next_action: str = "",
    ) -> CustomerFollowup:
        require_tenant_id(tenant_id)
        if not note.strip():
            raise ValueError("followup note is required")
        customer = self.repo.get_customer(tenant_id, customer_id)
        if not customer or customer.tenant_id != tenant_id:
            raise ValueError("customer not found for tenant")
        followup = CustomerFollowup(
            tenant_id=tenant_id,
            customer_id=customer_id,
            agent_id=agent_id,
            note=note.strip(),
            next_action=next_action.strip(),
        )
        return self.repo.add_followup(followup)

    def today_meetings(self, tenant_id: str, agent_id: str | None = None) -> list[Customer]:
        today = date.today()
        return [
            customer
            for customer in self.repo.list_customers(tenant_id, agent_id=agent_id)
            if customer.next_meeting_date == today
        ]

    def customer_history(self, tenant_id: str, customer_id: str) -> list[CustomerFollowup]:
        return self.repo.list_followups(tenant_id, customer_id)
