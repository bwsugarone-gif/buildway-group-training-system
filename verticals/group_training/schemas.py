"""Validation helpers for group training service inputs."""

from __future__ import annotations

from datetime import date

from verticals.group_training.models import CustomerStage, UserRole


def require_tenant_id(tenant_id: str) -> str:
    if not tenant_id or not isinstance(tenant_id, str):
        raise ValueError("tenant_id is required for all group training records")
    return tenant_id


def parse_role(value: str | UserRole) -> UserRole:
    if isinstance(value, UserRole):
        return value
    return UserRole(value)


def parse_customer_stage(value: str | CustomerStage) -> CustomerStage:
    if isinstance(value, CustomerStage):
        return value
    return CustomerStage(value)


def require_non_negative(value: int, field_name: str) -> int:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return value


def coerce_date(value: date | None) -> date:
    return value or date.today()

