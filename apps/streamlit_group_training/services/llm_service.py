"""
LLM Service for DeepSeek Hybrid Coaching Agent.

Rules:
- LLM only handles natural language explanation, coaching advice, follow-up messages.
- LLM CANNOT modify scores, risk levels, or database records.
- Agent role CANNOT see Hidden Score in any LLM prompt.
- If DEEPSEEK_API_KEY is not set, all functions fall back to rule-based text gracefully.
- All prompts instruct DeepSeek to reply in Traditional Chinese (Hong Kong insurance industry).
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
# System instruction: strict Traditional Chinese (HK) output
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "你是香港保險團隊培訓主管。\n\n"
    "所有輸出必須使用繁體中文。\n"
    "禁止使用英文標題。\n"
    "禁止使用英文段落。\n"
    "禁止使用簡體中文。\n"
    "請使用香港保險行業常用語氣。\n"
    "請以清晰、實用、可執行的條列方式回覆。"
)

# ---------------------------------------------------------------------------
# Post-processing: replace any English headings with Traditional Chinese
# ---------------------------------------------------------------------------

_EN_TO_ZH_HEADINGS = {
    "Today's Briefing:": "今日重點:",
    "Today's Briefing": "今日重點",
    "Main Bottleneck:": "主要瓶頸:",
    "Main Bottleneck": "主要瓶頸",
    "Priority Actions:": "優先行動:",
    "Priority Actions": "優先行動",
    "Coaching Insight:": "教練洞察:",
    "Coaching Insight": "教練洞察",
    "Action Steps:": "改善行動:",
    "Action Steps": "改善行動",
    "Follow-up Recommendation:": "跟進建議:",
    "Follow-up Recommendation": "跟進建議",
    "WhatsApp Opening:": "WhatsApp 開場句:",
    "WhatsApp Opening": "WhatsApp 開場句",
    "Coaching Analysis:": "教練洞察:",
    "Coaching Analysis": "教練洞察",
    "Today's Highlights:": "今日重點:",
    "Today's Highlights": "今日重點",
}


def _enforce_chinese_headings(text: str) -> str:
    """Replace common English headings with Traditional Chinese equivalents."""
    for en, zh in _EN_TO_ZH_HEADINGS.items():
        text = text.replace(en, zh)
    return text


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
    - Always prepends the HK Traditional Chinese system instruction
    - Post-processes to replace any English headings with Traditional Chinese
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
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.7,
        )
        result = response.choices[0].message.content or ""
        result = _enforce_chinese_headings(result)
        _llm_cache[ck] = result
        return result
    except Exception:
        return fallback


# ---------------------------------------------------------------------------
# Prompt builders — all in Traditional Chinese
# ---------------------------------------------------------------------------

def build_customer_followup_prompt(customer: Any, opportunity_analysis: Any) -> str:
    """
    Build a prompt asking DeepSeek to generate:
    1. A follow-up recommendation for this customer (繁體中文)
    2. A WhatsApp opening message (繁體中文)

    NOTE: Hidden Score is never included in this prompt.
    """
    stage = getattr(customer, "stage", None)
    stage_value = stage.value if hasattr(stage, "value") else str(stage)
    stage_zh = {
        "Cold": "冷（新名單）",
        "Warm": "暖（有興趣）",
        "Hot": "熱（高意向）",
        "Proposal": "方案（準備簽單）",
        "Closed": "已成交",
        "Lost": "已流失",
    }.get(stage_value, stage_value)

    notes = getattr(customer, "notes", "") or ""
    opp_score = getattr(opportunity_analysis, "opportunity_score", "N/A") if opportunity_analysis else "N/A"
    priority_raw = getattr(opportunity_analysis, "priority", "Medium") if opportunity_analysis else "Medium"
    priority_zh = {"High": "高", "Medium": "中", "Low": "低"}.get(str(priority_raw), str(priority_raw))

    return (
        f"客戶姓名：{getattr(customer, 'name', '未知')}\n"
        f"客戶階段：{stage_zh}\n"
        f"AI 機會分：{opp_score}（優先級：{priority_zh}）\n"
        f"備註：{notes[:200] if notes else '無'}\n\n"
        "請提供：\n"
        "1. 跟進建議：針對此客戶，給代理人 2-3 句具體的跟進方向。\n"
        "2. WhatsApp 開場句：代理人可以直接發送給客戶的 1-2 句親切專業開場白。\n\n"
        "請以以下格式輸出：\n"
        "跟進建議: [你的建議]\n"
        "WhatsApp 開場句: [你的開場白]"
    )


def build_agent_coaching_prompt(agent: Any, performance_analysis: Any, coaching_plan: Any) -> str:
    """
    Build a prompt for DeepSeek agent coaching advice in Traditional Chinese.

    NOTE: Hidden Score is deliberately excluded from this prompt (agent role restriction).
    """
    agent_name = getattr(agent, "name", None) or getattr(agent, "id", "代理")
    problem_stage = getattr(performance_analysis, "conversion_problem_stage", "activity_gap") if performance_analysis else "activity_gap"
    perf_score = getattr(performance_analysis, "performance_score", 0) if performance_analysis else 0
    metrics = getattr(performance_analysis, "metrics", {}) if performance_analysis else {}
    appt_rate = metrics.get("appointment_rate", 0)
    meeting_rate = metrics.get("meeting_rate", 0)
    closing_rate = metrics.get("closing_rate", 0)

    problem_zh = {
        "activity_gap": "活動量不足",
        "appointment_conversion": "預約轉化偏低",
        "meeting_conversion": "見客轉化偏低",
        "closing_conversion": "成交轉化偏低",
        "balanced_pipeline": "Pipeline 平衡",
    }.get(problem_stage, problem_stage)

    return (
        f"代理人：{agent_name}\n"
        f"表現分：{perf_score}/100\n"
        f"目前主要瓶頸：{problem_zh}\n"
        f"關鍵數據 — 預約率：{appt_rate:.1f}%、見客率：{meeting_rate:.1f}%、成交率：{closing_rate:.1f}%\n\n"
        "請提供：\n"
        "1. 教練洞察：用 2-3 句說明為何此代理人在這個階段遇到困難。\n"
        "2. 改善行動：列出 2 個具體、可執行的改善步驟。\n"
        "3. 跟進建議：主管下週應如何跟進此代理人。\n\n"
        "請以以下格式輸出：\n"
        "教練洞察: [你的分析]\n"
        "改善行動:\n"
        "- [步驟一]\n"
        "- [步驟二]\n"
        "跟進建議: [主管跟進方向]"
    )


def build_manager_briefing_prompt(
    team_metrics: dict,
    risk_agents: list,
    opportunity_customers: list,
) -> str:
    """
    Build a prompt for a manager's daily team briefing in Traditional Chinese.

    NOTE: Hidden Score raw values are not included — only risk counts are used.
    """
    total_agents = team_metrics.get("total_agents", 0)
    affected_agents = team_metrics.get("affected_agent_count", 0)
    high_risk_count = team_metrics.get("high_risk_agent_count", 0)
    top_customer_count = team_metrics.get("top_customer_count", 0)
    warm_count = team_metrics.get("warm_customer_count", 0)
    overdue_count = team_metrics.get("overdue_followup_count", 0)
    main_problem = team_metrics.get("main_problem", "activity_gap")
    problem_zh = {
        "activity_gap": "Pipeline 活動量不足",
        "appointment_conversion": "預約轉化偏低",
        "meeting_conversion": "見客確認不足",
        "closing_conversion": "成交轉化偏低",
        "balanced_pipeline": "Pipeline 穩定",
    }.get(main_problem, main_problem)

    risk_names = []
    for a in (risk_agents or [])[:5]:
        if isinstance(a, dict):
            risk_names.append(a.get("name") or a.get("id", ""))
        else:
            risk_names.append(str(a))

    top_customer_names = []
    for c in (opportunity_customers or [])[:5]:
        if isinstance(c, dict):
            top_customer_names.append(c.get("customer", str(c)))
        else:
            top_customer_names.append(str(c))

    return (
        f"今日團隊數據摘要：\n"
        f"- 代理總數：{total_agents} 人\n"
        f"- 主要瓶頸（{problem_zh}）影響代理數：{affected_agents} 人\n"
        f"- 高風險代理數：{high_risk_count} 人\n"
        f"- 今日高潛力客戶機會：{top_customer_count} 個\n"
        f"- Warm 客戶總數：{warm_count} 個\n"
        f"- 逾期跟進數：{overdue_count} 個\n"
        f"- 高風險代理：{('、'.join(risk_names)) if risk_names else '無'}\n"
        f"- 今日優先跟進客戶：{('、'.join(top_customer_names)) if top_customer_names else '無'}\n\n"
        "請以主管角度，提供今日團隊簡報，分三個部分：\n"
        "1. 今日重點：2-3 句總結今日團隊狀況，需包含具體數字。\n"
        "2. 主要瓶頸：1-2 句點出核心問題，如有高風險代理請點名。\n"
        "3. 優先行動：列出 3 個今日主管應執行的具體行動。\n\n"
        "必須使用以下格式輸出（繁體中文，不可使用英文）：\n"
        "今日重點: [簡報內容]\n"
        "主要瓶頸: [瓶頸說明]\n"
        "優先行動:\n"
        "- [行動一]\n"
        "- [行動二]\n"
        "- [行動三]"
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
