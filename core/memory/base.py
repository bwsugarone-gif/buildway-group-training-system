"""
core/memory/base.py
-------------------
Abstract interface for session memory and customer memory.
Concrete implementations (Supabase, JSON, SQLite) extend this base.
Placeholder — not connected to a real database yet.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """A single message within a chat session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    role: str = ""          # user | assistant | system
    content: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    """A chat session belonging to a tenant."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    customer_ref: str = ""  # WhatsApp number, email, CRM ID, etc.
    channel: str = "web"    # whatsapp | email | web | api
    summary: str = ""
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class BaseMemory(ABC):
    """
    Abstract memory interface.
    All tenant_id parameters are required — no cross-tenant access.
    """

    @abstractmethod
    def save_session(self, session: Session) -> str:
        """
        Persist a session. Returns the session ID.
        Creates a new record if session.id is new; updates if it exists.
        """
        ...

    @abstractmethod
    def load_sessions(self, tenant_id: str, customer_ref: str | None = None) -> list[Session]:
        """
        Load sessions for a tenant.
        Optionally filter by customer_ref (e.g. a specific WhatsApp number).
        """
        ...

    @abstractmethod
    def save_message(self, message: Message) -> str:
        """
        Persist a message. Returns the message ID.
        The parent session must already exist.
        """
        ...

    @abstractmethod
    def load_customer_memory(self, tenant_id: str, customer_ref: str) -> dict[str, Any]:
        """
        Load a summary of a customer's history for a given tenant.
        Returns a dict with keys: customer_ref, session_count, last_seen, summary.
        """
        ...


class InMemoryMemory(BaseMemory):
    """
    In-memory placeholder implementation for local dev and testing.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, Message] = {}

    def save_session(self, session: Session) -> str:
        self._sessions[session.id] = session
        return session.id

    def load_sessions(self, tenant_id: str, customer_ref: str | None = None) -> list[Session]:
        results = [s for s in self._sessions.values() if s.tenant_id == tenant_id]
        if customer_ref:
            results = [s for s in results if s.customer_ref == customer_ref]
        return sorted(results, key=lambda s: s.created_at)

    def save_message(self, message: Message) -> str:
        self._messages[message.id] = message
        if message.session_id in self._sessions:
            self._sessions[message.session_id].messages.append(message)
        return message.id

    def load_customer_memory(self, tenant_id: str, customer_ref: str) -> dict[str, Any]:
        sessions = self.load_sessions(tenant_id, customer_ref)
        return {
            "customer_ref": customer_ref,
            "session_count": len(sessions),
            "last_seen": sessions[-1].created_at.isoformat() if sessions else None,
            "summary": sessions[-1].summary if sessions else "",
        }
