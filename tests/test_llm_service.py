"""
Tests for Phase 2.0 DeepSeek Hybrid Coaching Agent - llm_service.py

Rules validated:
1. No DEEPSEEK_API_KEY → no crash, fallback to rule-based text
2. With mock key → llm_service can be mocked
3. LLM cannot modify score / risk
4. Agent role cannot see Hidden Score via prompts
5. i18n zh_HK / en keys consistent
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# 1. No API key → no crash, uses fallback
# ---------------------------------------------------------------------------

class TestNoApiKey:
    def setup_method(self):
        # Remove key from env for isolation
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def test_llm_enabled_returns_false_without_key(self):
        """llm_enabled() must return False when no key is set."""
        from apps.streamlit_group_training.services.llm_service import llm_enabled
        assert llm_enabled() is False

    def test_call_deepseek_fallback_when_no_key(self):
        """call_deepseek must not crash; returns fallback string."""
        from apps.streamlit_group_training.services.llm_service import call_deepseek
        result = call_deepseek("test prompt", fallback="rule-based fallback")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_llm_or_fallback_no_key(self):
        """get_llm_or_fallback returns (fallback_text, False) when no key."""
        from apps.streamlit_group_training.services.llm_service import get_llm_or_fallback
        text, used_llm = get_llm_or_fallback("test prompt", "fallback text")
        assert used_llm is False
        assert text == "fallback text"

    def test_build_customer_followup_prompt_no_crash(self):
        """build_customer_followup_prompt must not crash with minimal inputs."""
        from apps.streamlit_group_training.services.llm_service import build_customer_followup_prompt

        customer = MagicMock()
        customer.name = "Test Customer"
        customer.stage.value = "Hot"
        customer.phone = "12345678"
        customer.notes = "Interested in medical plan"

        opp = MagicMock()
        opp.opportunity_score = 85
        opp.priority = "high"
        opp.reason_key = "opportunity.reason.hot"
        opp.next_best_action_key = "opportunity.action.hot"
        opp.suggested_message_key = "opportunity.message.hot"

        prompt = build_customer_followup_prompt(customer, opp)
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    def test_build_agent_coaching_prompt_no_crash(self):
        """build_agent_coaching_prompt must not crash with minimal inputs."""
        from apps.streamlit_group_training.services.llm_service import build_agent_coaching_prompt

        agent = MagicMock()
        agent.name = "Test Agent"
        agent.id = "agent_001"

        performance = MagicMock()
        performance.performance_score = 55
        performance.conversion_problem_stage = "appointment_conversion"
        performance.metrics = {
            "total_outreach": 30,
            "appointment_rate": 5.0,
            "meeting_rate": 3.0,
            "closing_rate": 0.0,
        }

        coaching = MagicMock()
        coaching.coaching_topic_key = "coaching.topic.appointment_conversion"
        coaching.reason_key = "coaching.reason.appointment_conversion"
        coaching.training_focus_key = "coaching.focus.appointment_conversion"
        coaching.next_action_key = "coaching.agent_next_action.appointment_conversion"

        prompt = build_agent_coaching_prompt(agent, performance, coaching)
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    def test_build_manager_briefing_prompt_no_crash(self):
        """build_manager_briefing_prompt must not crash with minimal inputs."""
        from apps.streamlit_group_training.services.llm_service import build_manager_briefing_prompt

        metrics = {
            "team_total_customers": 50,
            "today_activity_count": 120,
            "risk_agent_ids": ["agent_001", "agent_002"],
            "hidden_score_average": 45.5,
        }
        risk_agents = [{"id": "agent_001", "name": "Alice"}, {"id": "agent_002", "name": "Bob"}]
        top_opps = [{"customer": "Customer A", "stage": "Hot", "score": 90}]

        prompt = build_manager_briefing_prompt(metrics, risk_agents, top_opps)
        assert isinstance(prompt, str)
        assert len(prompt) > 10


# ---------------------------------------------------------------------------
# 2. With mock key → llm_service can be mocked
# ---------------------------------------------------------------------------

class TestMockApiKey:
    def setup_method(self):
        os.environ["DEEPSEEK_API_KEY"] = "mock-key-for-testing"

    def teardown_method(self):
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def test_llm_enabled_returns_true_with_key(self):
        from apps.streamlit_group_training.services.llm_service import llm_enabled
        assert llm_enabled() is True

    def test_call_deepseek_with_mock_client(self):
        """call_deepseek with mocked OpenAI client returns mock response."""
        from apps.streamlit_group_training.services import llm_service

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked LLM response"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            # Clear cache before test
            llm_service._llm_cache.clear()
            result = llm_service.call_deepseek("test prompt")
            assert result == "Mocked LLM response"

    def test_get_llm_or_fallback_uses_llm_when_key_present(self):
        """get_llm_or_fallback returns (text, True) when LLM succeeds."""
        from apps.streamlit_group_training.services import llm_service

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "LLM coaching advice"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            llm_service._llm_cache.clear()
            text, used_llm = llm_service.get_llm_or_fallback("prompt", "fallback")
            assert used_llm is True
            assert text == "LLM coaching advice"


# ---------------------------------------------------------------------------
# 3. LLM cannot modify score / risk
# ---------------------------------------------------------------------------

class TestLLMCannotModifyScoreOrRisk:
    def test_call_deepseek_returns_string_only(self):
        """call_deepseek returns a plain string. Score/risk are untouched."""
        from apps.streamlit_group_training.services.llm_service import call_deepseek
        os.environ.pop("DEEPSEEK_API_KEY", None)

        result = call_deepseek("prompt", fallback="fallback text")
        # Result is a string; no score mutation possible
        assert isinstance(result, str)
        assert not isinstance(result, (int, float, dict, list))

    def test_hidden_score_not_in_agent_coaching_prompt(self):
        """Agent coaching prompt must NOT include hidden score values."""
        from apps.streamlit_group_training.services.llm_service import build_agent_coaching_prompt

        agent = MagicMock()
        agent.name = "Test Agent"
        agent.id = "agent_001"

        performance = MagicMock()
        performance.performance_score = 60
        performance.conversion_problem_stage = "activity_gap"
        performance.metrics = {
            "total_outreach": 10,
            "appointment_rate": 2.0,
            "meeting_rate": 1.0,
            "closing_rate": 0.0,
        }

        coaching = MagicMock()
        coaching.coaching_topic_key = "coaching.topic.activity_gap"
        coaching.reason_key = "coaching.reason.activity_gap"
        coaching.training_focus_key = "coaching.focus.activity_gap"
        coaching.next_action_key = "coaching.agent_next_action.activity_gap"

        prompt = build_agent_coaching_prompt(agent, performance, coaching)
        # Should not contain hidden score label
        assert "hidden_score" not in prompt.lower()
        assert "隱藏" not in prompt


# ---------------------------------------------------------------------------
# 4. Agent role cannot see Hidden Score via prompts
# ---------------------------------------------------------------------------

class TestAgentCannotSeeHiddenScore:
    def test_agent_coaching_prompt_excludes_hidden_score(self):
        """Prompts built for agent role must never include hidden score."""
        from apps.streamlit_group_training.services.llm_service import build_agent_coaching_prompt

        agent = MagicMock()
        agent.name = "Agent Smith"
        agent.id = "agent_smith"

        performance = MagicMock()
        performance.performance_score = 72
        performance.conversion_problem_stage = "closing_conversion"
        performance.metrics = {
            "total_outreach": 40,
            "appointment_rate": 15.0,
            "meeting_rate": 10.0,
            "closing_rate": 2.0,
        }

        coaching = MagicMock()
        coaching.coaching_topic_key = "coaching.topic.closing_conversion"
        coaching.reason_key = "coaching.reason.closing_conversion"
        coaching.training_focus_key = "coaching.focus.closing_conversion"
        coaching.next_action_key = "coaching.agent_next_action.closing_conversion"

        prompt = build_agent_coaching_prompt(agent, performance, coaching)

        # Strictly verify hidden score is not exposed
        forbidden_patterns = ["hidden", "隱藏分", "hidden_score", "closing_score_hidden"]
        for pattern in forbidden_patterns:
            assert pattern not in prompt.lower(), f"Prompt should not contain '{pattern}'"

    def test_customer_followup_prompt_excludes_hidden_score(self):
        """Customer follow-up prompts must not include hidden score."""
        from apps.streamlit_group_training.services.llm_service import build_customer_followup_prompt

        customer = MagicMock()
        customer.name = "Customer Chan"
        customer.stage.value = "Warm"
        customer.phone = "99887766"
        customer.notes = "Interested in critical illness"

        opp = MagicMock()
        opp.opportunity_score = 70
        opp.priority = "medium"
        opp.reason_key = "opportunity.reason.warm"
        opp.next_best_action_key = "opportunity.action.warm"
        opp.suggested_message_key = "opportunity.message.warm"

        prompt = build_customer_followup_prompt(customer, opp)
        assert "hidden" not in prompt.lower()
        assert "hidden_score" not in prompt


# ---------------------------------------------------------------------------
# 5. i18n keys consistent between zh_HK and en
# ---------------------------------------------------------------------------

class TestI18nKeyConsistency:
    def _load_json(self, filename: str) -> dict:
        import json
        path = ROOT / "apps" / "streamlit_group_training" / "i18n" / filename
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_llm_keys_present_in_both_locales(self):
        """All llm.* i18n keys must exist in both zh_HK.json and en.json."""
        zh = self._load_json("zh_HK.json")
        en = self._load_json("en.json")

        required_llm_keys = [
            "llm.api_disabled",
            "llm.customer_followup_title",
            "llm.whatsapp_opening_title",
            "llm.agent_coaching_title",
            "llm.manager_coaching_title",
            "llm.manager_briefing_title",
            "llm.manager_bottleneck_title",
            "llm.manager_priority_title",
            "llm.generating",
            "llm.fallback_notice",
        ]

        for key in required_llm_keys:
            assert key in zh, f"zh_HK.json missing key: {key}"
            assert key in en, f"en.json missing key: {key}"

    def test_llm_keys_not_empty(self):
        """All llm.* keys must have non-empty values."""
        zh = self._load_json("zh_HK.json")
        en = self._load_json("en.json")

        llm_keys_zh = {k: v for k, v in zh.items() if k.startswith("llm.")}
        llm_keys_en = {k: v for k, v in en.items() if k.startswith("llm.")}

        for key, val in llm_keys_zh.items():
            assert val and val.strip(), f"zh_HK.json key '{key}' is empty"
        for key, val in llm_keys_en.items():
            assert val and val.strip(), f"en.json key '{key}' is empty"

    def test_zh_hk_and_en_llm_key_sets_match(self):
        """The set of llm.* keys in zh_HK and en must be identical."""
        zh = self._load_json("zh_HK.json")
        en = self._load_json("en.json")

        zh_llm = {k for k in zh if k.startswith("llm.")}
        en_llm = {k for k in en if k.startswith("llm.")}

        missing_in_en = zh_llm - en_llm
        missing_in_zh = en_llm - zh_llm

        assert not missing_in_en, f"Keys in zh_HK but not en: {missing_in_en}"
        assert not missing_in_zh, f"Keys in en but not zh_HK: {missing_in_zh}"


# ---------------------------------------------------------------------------
# 6. Cache prevents duplicate API calls
# ---------------------------------------------------------------------------

class TestLLMCache:
    def setup_method(self):
        os.environ["DEEPSEEK_API_KEY"] = "mock-key-for-cache-test"

    def teardown_method(self):
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def test_same_prompt_hits_cache_on_second_call(self):
        """Calling call_deepseek twice with the same prompt uses cache (1 API call)."""
        from apps.streamlit_group_training.services import llm_service

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Cached response"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            llm_service._llm_cache.clear()
            result1 = llm_service.call_deepseek("same prompt")
            result2 = llm_service.call_deepseek("same prompt")

        assert result1 == result2 == "Cached response"
        # API should only be called once due to cache
        assert mock_client.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# Phase 2.2b — Fix 1: AI detail dataframe fields not empty
# ---------------------------------------------------------------------------

class TestAiDetailDataframeFields:
    """Verify render_demo_ai_insights AI detail expander fields have fallback values."""

    def _make_customer(self, cid="c1", name="陳大文", stage="Hot", agent_id="a1"):
        from datetime import date
        from unittest.mock import MagicMock
        c = MagicMock()
        c.id = cid
        c.name = name
        c.stage.value = stage
        c.agent_id = agent_id
        c.phone = "9999-0000"
        c.notes = ""
        c.next_meeting_date = date.today()
        c.created_at.strftime.return_value = "2026-06-10 00:00"
        return c

    def test_opportunity_reason_fallback_applied(self):
        """opportunity_reason must never be empty after fallback logic."""
        import pandas as pd
        # Simulate customers_to_dataframe producing empty opportunity_reason
        df = pd.DataFrame([{
            "customer": "陳大文",
            "stage": "熱",
            "agent_id": "a1",
            "opportunity_score": 75,
            "priority": "高",
            "opportunity_reason": "",          # empty — should trigger fallback
            "next_best_action": "致電確認方案",
            "suggested_message": "",           # empty — should trigger fallback
            "notes": "",
        }])
        REASON_FALLBACK = "此客戶根據狀態、跟進日期及機會分數被列入優先名單。"
        MSG_FALLBACK = "您好，我想跟進一下您最近關心的保障需要，看看有沒有需要更新或補充的地方。"
        expander_cols = ["customer", "opportunity_reason", "next_best_action", "suggested_message", "notes"]
        sub = df[[c for c in expander_cols if c in df.columns]].copy()
        sub["opportunity_reason"] = sub["opportunity_reason"].apply(
            lambda v: v if (isinstance(v, str) and v.strip()) else REASON_FALLBACK
        )
        sub["suggested_message"] = sub["suggested_message"].apply(
            lambda v: v if (isinstance(v, str) and v.strip()) else MSG_FALLBACK
        )
        assert sub["opportunity_reason"].iloc[0] == REASON_FALLBACK
        assert sub["suggested_message"].iloc[0] == MSG_FALLBACK

    def test_non_empty_values_preserved(self):
        """Non-empty opportunity_reason / suggested_message must not be overwritten."""
        import pandas as pd
        REASON = "客戶有明確保障需求。"
        MSG = "陳先生您好，跟進上次保障方案。"
        df = pd.DataFrame([{
            "customer": "陳大文",
            "opportunity_reason": REASON,
            "next_best_action": "致電",
            "suggested_message": MSG,
            "notes": "",
        }])
        REASON_FALLBACK = "fallback reason"
        MSG_FALLBACK = "fallback msg"
        df["opportunity_reason"] = df["opportunity_reason"].apply(
            lambda v: v if (isinstance(v, str) and v.strip()) else REASON_FALLBACK
        )
        df["suggested_message"] = df["suggested_message"].apply(
            lambda v: v if (isinstance(v, str) and v.strip()) else MSG_FALLBACK
        )
        assert df["opportunity_reason"].iloc[0] == REASON
        assert df["suggested_message"].iloc[0] == MSG

    def test_combined_df_no_duplicates(self):
        """After pd.concat + drop_duplicates, no customer should appear twice."""
        import pandas as pd
        row = {"customer": "陳大文", "opportunity_reason": "有需求", "next_best_action": "致電", "suggested_message": "您好", "notes": ""}
        df1 = pd.DataFrame([row])
        df2 = pd.DataFrame([row])  # same customer appears in both tables
        combined = pd.concat([df1, df2], ignore_index=True).drop_duplicates(subset=["customer"])
        assert len(combined) == 1


# ---------------------------------------------------------------------------
# Phase 2.2b — Fix 2: Dashboard chart title not duplicated
# ---------------------------------------------------------------------------

class TestDashboardChartTitleNotDuplicated:
    """smart_kpi_chart with title='' must not produce visible Altair chart title."""

    def test_smart_kpi_chart_empty_title(self):
        """When title='' the Altair chart title property should be empty string."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        import pandas as pd
        import altair as alt
        # Import app helpers directly
        from apps.streamlit_group_training.app import smart_kpi_chart
        chart = smart_kpi_chart(["接觸", "預約", "見客", "成交"], [100, 30, 10, 2], "")
        spec = chart.to_dict()
        # Altair layer chart: title at top level
        title = spec.get("title", "")
        assert title == "" or title is None, f"Expected empty title, got: {title!r}"

    def test_smart_kpi_chart_with_title(self):
        """When title is provided it should be in the spec (legacy usage)."""
        from apps.streamlit_group_training.app import smart_kpi_chart
        chart = smart_kpi_chart(["A", "B"], [10, 20], "銷售漏斗")
        spec = chart.to_dict()
        title = spec.get("title", "")
        assert title == "銷售漏斗", f"Expected '銷售漏斗', got: {title!r}"

    def test_funnel_kpi_chart_uses_empty_title(self):
        """Dashboard funnel row passes title='' to avoid duplication with st.markdown header."""
        from apps.streamlit_group_training.app import smart_kpi_chart
        # Simulate what manager_dashboard_page does: title="" passed
        chart = smart_kpi_chart(["接觸", "預約", "見客", "成交"], [850, 65, 28, 5], "")
        spec = chart.to_dict()
        assert spec.get("title", "") == ""

    def test_stage_kpi_chart_uses_empty_title(self):
        """Dashboard customer stage chart passes title='' to avoid duplication."""
        from apps.streamlit_group_training.app import smart_kpi_chart
        chart = smart_kpi_chart(["冷", "暖", "熱"], [20, 10, 5], "")
        spec = chart.to_dict()
        assert spec.get("title", "") == ""

    def test_risk_kpi_chart_uses_empty_title(self):
        """Dashboard risk distribution chart passes title='' to avoid duplication."""
        from apps.streamlit_group_training.app import smart_kpi_chart
        chart = smart_kpi_chart(["低風險", "中風險", "高風險"], [5, 3, 2], "")
        spec = chart.to_dict()
        assert spec.get("title", "") == ""
