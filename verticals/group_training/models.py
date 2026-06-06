"""
Domain models for the insurance group training MVP.

All SaaS-owned records include tenant_id to preserve tenant isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class UserRole(str, Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    AGENT = "Agent"


class CustomerStage(str, Enum):
    COLD = "Cold"
    WARM = "Warm"
    HOT = "Hot"
    PROPOSAL = "Proposal"
    CLOSED = "Closed"
    LOST = "Lost"


@dataclass
class User:
    tenant_id: str
    id: str
    name: str
    email: str
    role: UserRole
    team_id: str | None = None
    manager_id: str | None = None
    password_hash: str = ""


@dataclass
class Team:
    tenant_id: str
    id: str
    name: str
    manager_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Customer:
    tenant_id: str
    team_id: str
    agent_id: str
    name: str
    stage: CustomerStage
    phone: str = ""
    notes: str = ""
    next_meeting_date: date | None = None
    id: str = field(default_factory=lambda: new_id("cust"))
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CustomerFollowup:
    tenant_id: str
    customer_id: str
    agent_id: str
    note: str
    next_action: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: new_id("follow"))


@dataclass
class DailyActivityLog:
    tenant_id: str
    team_id: str
    agent_id: str
    activity_date: date
    call_count: int = 0
    whatsapp_count: int = 0
    appointment_count: int = 0
    meeting_count: int = 0
    closing_count: int = 0
    notes: str = ""
    id: str = field(default_factory=lambda: new_id("log"))
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AITrainingReview:
    tenant_id: str
    team_id: str
    agent_id: str
    review_date: date
    summary: str
    improvement_advice: str
    manager_feedback: str
    risk_level: str
    id: str = field(default_factory=lambda: new_id("review"))
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ClosingScore:
    tenant_id: str
    team_id: str
    agent_id: str
    score_date: date
    hidden_score: int
    rationale: str
    id: str = field(default_factory=lambda: new_id("score"))
    created_at: datetime = field(default_factory=datetime.utcnow)
