# -*- coding: utf-8 -*-
"""
verticals/crm/customer_memory.py
Buildway AI Core — CRM Vertical: Customer Memory Manager

Extends core session memory with CRM-specific customer context.
Storage: JSON file (data/crm_customers.json)

Customer record schema:
{
    "customer_id":    "CUS-20260516-abc1",
    "name":           "Acme Corp",
    "contact_name":   "John Chan",
    "contact_email":  "john@acme.com",
    "contact_phone":  "+852 1234 5678",
    "tier":           "enterprise",
    "tags":           ["vip", "construction"],
    "notes":          "Key account since 2024.",
    "created_at":     "2026-05-16T14:30:22",
    "updated_at":     "2026-05-16T14:30:22",
    "interactions":   []
}
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_CUSTOMERS_FILE = _DATA_DIR / "crm_customers.json"
_MAX_INTERACTIONS_PER_CUSTOMER = 50

CUSTOMER_TIERS = ["standard", "premium", "enterprise"]


def _ensure_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_all() -> list:
    _ensure_dir()
    if not _CUSTOMERS_FILE.exists():
        return []
    try:
        data = json.loads(_CUSTOMERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_all(customers: list) -> None:
    _ensure_dir()
    _CUSTOMERS_FILE.write_text(
        json.dumps(customers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_customer(
    name: str,
    contact_name: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    tier: str = "standard",
    tags: list[str] | None = None,
    notes: str = "",
) -> dict:
    """Create a new customer record. Returns the created customer dict."""
    customer = {
        "customer_id": f"CUS-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}",
        "name": str(name or "").strip(),
        "contact_name": str(contact_name or "").strip(),
        "contact_email": str(contact_email or "").strip(),
        "contact_phone": str(contact_phone or "").strip(),
        "tier": tier if tier in CUSTOMER_TIERS else "standard",
        "tags": list(tags or []),
        "notes": str(notes or "").strip(),
        "created_at": _now(),
        "updated_at": _now(),
        "interactions": [],
    }
    customers = _load_all()
    customers.append(customer)
    _save_all(customers)
    return customer


def get_customer(customer_id: str) -> dict | None:
    """Get a customer by ID."""
    for c in _load_all():
        if c.get("customer_id") == customer_id:
            return c
    return None


def find_customers(query: str) -> list[dict]:
    """Search customers by name, contact name, or email."""
    q = query.lower().strip()
    return [
        c for c in _load_all()
        if q in c.get("name", "").lower()
        or q in c.get("contact_name", "").lower()
        or q in c.get("contact_email", "").lower()
    ]


def add_interaction(
    customer_id: str,
    interaction_type: str,
    summary: str,
    agent_id: str = "",
    metadata: dict | None = None,
) -> dict | None:
    """
    Add an interaction record to a customer.

    interaction_type: e.g. 'email', 'call', 'meeting', 'ai_analysis'
    Returns the updated customer, or None if not found.
    """
    customers = _load_all()
    for customer in customers:
        if customer.get("customer_id") == customer_id:
            interaction = {
                "interaction_id": f"INT-{uuid.uuid4().hex[:8]}",
                "type": interaction_type,
                "summary": str(summary or ""),
                "agent_id": str(agent_id or ""),
                "metadata": metadata or {},
                "timestamp": _now(),
            }
            interactions = customer.setdefault("interactions", [])
            interactions.append(interaction)
            # Cap interactions
            if len(interactions) > _MAX_INTERACTIONS_PER_CUSTOMER:
                customer["interactions"] = interactions[-_MAX_INTERACTIONS_PER_CUSTOMER:]
            customer["updated_at"] = _now()
            _save_all(customers)
            return customer
    return None


def list_customers(tier: str | None = None) -> list[dict]:
    """List all customers, optionally filtered by tier."""
    customers = _load_all()
    if tier:
        customers = [c for c in customers if c.get("tier") == tier]
    return sorted(customers, key=lambda c: c.get("name", ""))
