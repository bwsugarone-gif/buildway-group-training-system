"""
core/tenant/context.py
----------------------
Tenant context management for multi-tenant SaaS isolation.
Every request must carry a valid tenant_id — no cross-tenant access.
Placeholder — not connected to a real database yet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable context object representing the current tenant.
    Pass this through the call stack instead of raw tenant_id strings.
    """
    tenant_id: str
    tenant_name: str = ""
    industry: str = ""      # construction | crm | erp | document_ai
    status: str = "active"  # active | suspended | trial


# ---------------------------------------------------------------------------
# In-memory tenant registry (placeholder — replace with DB lookup in Phase 2)
# ---------------------------------------------------------------------------

_TENANT_REGISTRY: dict[str, TenantContext] = {}


def register_tenant(
    tenant_id: str,
    tenant_name: str = "",
    industry: str = "",
    status: str = "active",
) -> TenantContext:
    """
    Register a tenant in the in-memory registry.
    Used for local dev and testing only.
    """
    ctx = TenantContext(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        industry=industry,
        status=status,
    )
    _TENANT_REGISTRY[tenant_id] = ctx
    return ctx


def validate_tenant_id(tenant_id: str) -> bool:
    """
    Validate that a tenant_id is a non-empty, well-formed UUID string.
    Does NOT check whether the tenant exists in the database.
    Use get_current_tenant() for existence checks.
    """
    if not tenant_id or not isinstance(tenant_id, str):
        return False
    try:
        uuid.UUID(tenant_id)
        return True
    except ValueError:
        return False


def get_current_tenant(tenant_id: str) -> Optional[TenantContext]:
    """
    Look up a tenant by ID.
    Returns TenantContext if found, None if not registered.

    In Phase 2 this will query the tenants table in Supabase.
    For now it checks the in-memory registry.
    """
    if not validate_tenant_id(tenant_id):
        return None
    return _TENANT_REGISTRY.get(tenant_id)


def require_tenant(tenant_id: str) -> TenantContext:
    """
    Like get_current_tenant() but raises ValueError if not found.
    Use this in request handlers where a valid tenant is mandatory.
    """
    ctx = get_current_tenant(tenant_id)
    if ctx is None:
        raise ValueError(
            f"Tenant not found or invalid tenant_id: {tenant_id!r}. "
            f"Ensure the tenant is registered before making requests."
        )
    if ctx.status != "active":
        raise ValueError(
            f"Tenant {tenant_id!r} is not active (status={ctx.status!r}). "
            f"Contact Buildway support."
        )
    return ctx
