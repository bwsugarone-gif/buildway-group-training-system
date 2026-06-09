"""
LLM Service for DeepSeek Hybrid Coaching Agent.

Rules:
- LLM only handles natural language explanation, coaching advice, follow-up messages.
- LLM CANNOT modify scores, risk levels, or database records.
- Agent role CANNOT see Hidden Score in any LLM prompt.
- If DEEPSEEK_API_KEY is not set, all functions fall back to rule-based text gracefully.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

# ---------------------------------------------------------------------------
# API key resolution (supports st.secrets and os.getenv)
# ---------------------------------------------------------------------------

def _get_api_key() -> str | None:
    """Resolve DEEPSEEK_API_KEY from st.secrets or environment variable."""
    # Try Streamlit secrets first (won't crash if not in Streamlit context)
    try:
        import streamlit as st
        key = st.secrets.get("DEEPSEEK_API_KEY", None)
        if key:
            return str(key)
    except Exception:
        pass
    return os.getenv("DEEPSEEK_API_KEY")


def llm_enabled() -> bool:
    """Return True if a DeepSeek API key is available."""
    return bool(_get_api_key())


# ---------------------------------------------------------------------------
# Simple in-process cache keyed by prompt hash (reset on process restart)
# ---------------------------------------------------------------------------

_llm_cache: dict[str, str] = {}
# Alias for backward compatibility
_CACHE = _llm_cache


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Client factory (isolated for easy mocking in tests)
# ---------------------------------------------------------------------------

def _get_client():
    """Return an OpenAI-compatible client pointed at DeepSeek."""
    from openai import OpenAI
    return OpenAI(
        api_key=_get_api_key(),
        base_url="https://api.deepseek.com",
        timeout=30.0,
    )


# ---------------------------------------------------------------------------
# Core DeepSeek caller
# ---------------------------------------------------------------------------

def call_deepseek(prompt: str, fallback: str = "") -> str:
    """
    Call DeepSeek chat API and return the response text.

    - Uses OpenAI SDK compatible mode with base_url=https://api.deepseek.com
    - 30-second timeout
    - Simple in-process cache to avoid duplicate API calls within the same session
    - Falls back to `fallback` string on any error or missing key
    """
    api_key = _get_api_key()
    if not api_key:
        return fallback

    ck = _cache_key(prompt)
    if ck in _llm_cache:
        return _llm_cache[ck]

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.7,
        )
        result = response.choices[0].message.content or ""
        _llm_cache[ck] = result
        return result
    except Exception:
        return fallback


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_customer_followup_prompt(customer: Any, opportunity_analysis: Any) -> str:
    """
    Build a prompt asking DeepSeek to generate:
    1. A follow-up recommendation for this customer
    2. A WhatsApp opening message

    NOTE: Hidden Score is never included in this prompt.
    """
    stage = getattr(customer, "stage", None)
    stage_value = stage.value if hasattr(stage, "value") else str(stage)
    notes = getattr(customer, "notes", "") or ""
    opp_score = getattr(opportunity_analysis, "opportunity_score", "N/A") if opportunity_analysis else "N/A"
    priority = getattr(opportunity_analysis, "priority", "Medium") if opportunity_analysis else "Medium"

    return (
        f"You are an insurance sales coach. A customer named {getattr(customer, 'name', 'Unknown')} "
        f"is currently at the '{stage_value}' stage with an AI opportunity score of {opp_score} "
        f"(priority: {priority}). Notes: {notes[:200] if notes else 'None'}.\n\n"
        "Please provide:\n"
        "1. A brief follow-up recommendation (2-3 sentences) for the agent.\n"
        "2. A WhatsApp opening message the agent can send directly to this customer (1-2 sentences, friendly and professional).\n\n"
        "Format your response as:\n"
        "Follow-up Recommendation: [your recommendation]\n"
        "WhatsApp Opening: [your message]"
    )


def build_agent_coaching_prompt(agent: Any, performance_analysis: Any, coaching_plan: Any) -> str:
    """
    Build a prompt for DeepSeek agent coaching advice.

    NOTE: Hidden Score is deliberately excluded from this prompt (agent role restriction).
    """
    agent_name = getattr(agent, "name", None) or getattr(agent, "id", "Agent")
    problem_stage = getattr(performance_analysis, "conversion_problem_stage", "activity_gap") if performance_analysis else "activity_gap"
    perf_score = getattr(performance_analysis, "performance_score", 0) if performance_analysis else 0
    metrics = getattr(performance_analysis, "metrics", {}) if performance_analysis else {}
    appt_rate = metrics.get("appointment_rate", 0)
    meeting_rate = metrics.get("meeting_rate", 0)
    closing_rate = metrics.get("closing_rate", 0)
    topic_key = getattr(coaching_plan, "coaching_topic_key", "") if coaching_plan else ""
    topic = topic_key.split(".")[-1].replace("_", " ") if topic_key else problem_stage.replace("_", " ")

    return (
        f"You are an expert insurance sales manager providing coaching advice.\n"
        f"Agent: {agent_name}\n"
        f"Performance score: {perf_score}/100\n"
        f"Current bottleneck: {problem_stage.replace('_', ' ')}\n"
        f"Key metrics — Appointment rate: {appt_rate:.1f}%, Meeting rate: {meeting_rate:.1f}%, Closing rate: {closing_rate:.1f}%\n"
        f"Coaching focus: {topic}\n\n"
        "Please provide:\n"
        "1. A concise coaching insight (2-3 sentences) explaining why this agent is struggling.\n"
        "2. Two specific action steps the agent should take this week.\n\n"
        "Format your response as:\n"
        "Coaching Insight: [your insight]\n"
        "Action Steps:\n"
        "- [step 1]\n"
        "- [step 2]"
    )


def build_manager_briefing_prompt(
    team_metrics: dict,
    risk_agents: list,
    opportunity_customers: list,
) -> str:
    """
    Build a prompt for a manager's daily team briefing.

    NOTE: Hidden Score raw values are not included — only risk counts are used.
    """
    total_agents = team_metrics.get("total_agents", 0)
    affected_agents = team_metrics.get("affected_agent_count", 0)
    high_risk_count = team_metrics.get("high_risk_agent_count", 0)
    top_customer_count = team_metrics.get("top_customer_count", 0)
    main_problem = team_metrics.get("main_problem", "activity_gap").replace("_", " ")
    risk_names = [str(a) for a in (risk_agents or [])[:5]]
    top_customer_names = [str(c) for c in (opportunity_customers or [])[:5]]

    return (
        f"You are an AI assistant for an insurance team manager. Here is today's team snapshot:\n"
        f"- Total agents: {total_agents}\n"
        f"- Agents affected by main bottleneck ({main_problem}): {affected_agents}\n"
        f"- High-risk agents: {high_risk_count}\n"
        f"- Top customer opportunities today: {top_customer_count}\n"
        f"- Risk agents: {', '.join(risk_names) if risk_names else 'None'}\n"
        f"- Top customers to follow up: {', '.join(top_customer_names) if top_customer_names else 'None'}\n\n"
        "Please provide a manager's daily briefing in 3 sections:\n"
        "1. Today's Briefing (2-3 sentences summarising the team situation)\n"
        "2. Main Team Bottleneck (1-2 sentences identifying the core issue)\n"
        "3. Today's Priority Actions (2-3 bullet points the manager should take today)\n\n"
        "Format your response as:\n"
        "Today's Briefing: [briefing]\n"
        "Main Bottleneck: [bottleneck]\n"
        "Priority Actions:\n"
        "- [action 1]\n"
        "- [action 2]\n"
        "- [action 3]"
    )


# ---------------------------------------------------------------------------
# High-level helper: get LLM text or fallback
# ---------------------------------------------------------------------------

def get_llm_or_fallback(prompt: str, fallback: str) -> tuple[str, bool]:
    """
    Call DeepSeek with prompt.  Returns (text, used_llm).
    If API key is missing or call fails, returns (fallback, False).
    """
    if not llm_enabled():
        return fallback, False
    result = call_deepseek(prompt)
    if not result:
        return fallback, False
    return result, True


def clear_cache() -> None:
    """Clear the in-process response cache (useful for testing)."""
    _llm_cache.clear()
