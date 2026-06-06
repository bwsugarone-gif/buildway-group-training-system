from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "apps" / "streamlit_demo" / "app.py"


def test_crm_blocks_without_api_key_and_has_no_template_fallback():
    source = APP_PATH.read_text(encoding="utf-8")

    assert "No AI model configured. Please complete AI Model Setup first." in source
    assert "_generate_template_reply" not in source
    assert "Template (no API key)" not in source
    assert "Template reply will be used as fallback." not in source


def test_crm_uses_openai_api_source_and_persists_configured_status():
    source = APP_PATH.read_text(encoding="utf-8")

    assert 'st.session_state["ai_provider_configs"][provider]' in source
    assert 'st.session_state["ai_provider"] = config.provider' in source
    assert 'st.session_state["ai_model"] = config.model' in source
    assert 'st.session_state["ai_api_key"] = config.api_key' in source
    assert '"OpenAI API"' in source
    assert '"OpenAI-Compatible API"' in source


def test_multi_provider_ui_and_non_openai_placeholder_are_present():
    source = APP_PATH.read_text(encoding="utf-8")

    assert "SUPPORTED_PROVIDERS" in source
    assert "PROVIDER_MODELS[provider]" in source
    assert "provider_requires_base_url(provider)" in source
    assert "Provider integration coming in next phase." in source or "COMING_SOON_MESSAGE" in source
