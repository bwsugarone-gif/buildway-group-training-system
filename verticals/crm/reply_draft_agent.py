# -*- coding: utf-8 -*-
"""
verticals/crm/reply_draft_agent.py
Buildway AI Core — CRM Vertical: Reply Draft Agent

Generates draft replies to customer communications using LLM.
Supports email, chat, and formal letter formats.
"""

from pathlib import Path
from typing import Any


REPLY_FORMATS = ["email", "chat", "formal_letter", "internal_note"]

REPLY_TONES = ["professional", "friendly", "formal", "empathetic", "concise"]

# Default system prompt for reply drafting
_DEFAULT_SYSTEM_PROMPT = """You are a professional customer communications assistant.
Your task is to draft a reply to a customer message.

Guidelines:
- Be clear, concise, and professional
- Address all points raised by the customer
- Avoid making promises that cannot be kept
- Escalate if the issue is beyond your scope
- Use the customer's name if available
"""


def build_reply_prompt(
    customer_message: str,
    customer_name: str = "",
    context_docs: list[str] | None = None,
    format: str = "email",
    tone: str = "professional",
    extra_instructions: str = "",
) -> str:
    """
    Build a prompt for drafting a customer reply.

    Args:
        customer_message: The customer's original message.
        customer_name: Customer's name (optional).
        context_docs: Relevant document chunks from RAG (optional).
        format: Reply format (email, chat, formal_letter, internal_note).
        tone: Reply tone.
        extra_instructions: Any additional instructions.

    Returns:
        Formatted prompt string.
    """
    parts = [_DEFAULT_SYSTEM_PROMPT, ""]

    if customer_name:
        parts.append(f"Customer Name: {customer_name}")

    parts += [
        f"Reply Format: {format}",
        f"Tone: {tone}",
        "",
        "## Customer Message",
        customer_message.strip(),
    ]

    if context_docs:
        parts += [
            "",
            "## Relevant Context (from knowledge base)",
        ]
        for i, doc in enumerate(context_docs[:3], 1):
            parts.append(f"[{i}] {doc[:500]}...")

    if extra_instructions:
        parts += ["", "## Additional Instructions", extra_instructions.strip()]

    parts += [
        "",
        "## Task",
        f"Draft a {tone} {format} reply to the customer message above.",
        "Address all points raised. Be helpful and accurate.",
        "Output only the reply text, ready to send.",
    ]

    return "\n".join(parts)


def parse_draft_response(llm_response: str) -> dict[str, Any]:
    """
    Parse the LLM response into a structured draft.

    Returns:
        Dict with keys: subject (if email), body, word_count.
    """
    text = str(llm_response or "").strip()

    # Try to extract subject line for emails
    subject = ""
    body = text
    lines = text.split("\n")
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0][8:].strip()
        body = "\n".join(lines[1:]).strip()

    return {
        "subject": subject,
        "body": body,
        "word_count": len(body.split()),
    }
