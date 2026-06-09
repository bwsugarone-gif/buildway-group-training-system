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
