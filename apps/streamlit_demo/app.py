# -*- coding: utf-8 -*-
"""
apps/streamlit_demo/app.py
Buildway AI Core — SaaS Onboarding Demo (Phase 0.4A)
CRM AI Reply Workflow MVP: real OpenAI API reply with session state.
API keys never stored or committed.
"""

import os
import sys
from pathlib import Path

# Set protobuf implementation before importing any protobuf-dependent packages
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from core.agents.provider_router import (
    AIProviderConfig,
    AVAILABLE_PROVIDERS,
    COMING_SOON_MESSAGE,
    COMING_SOON_PROVIDERS,
    ConnectionResult,
    CONNECTION_REQUIRED_MESSAGE,
    CRM_PROVIDER_UNAVAILABLE_MESSAGE,
    DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH,
    OpenAICompatibleRequestError,
    PROVIDER_KEY_LABELS,
    PROVIDER_KEY_PLACEHOLDERS,
    PROVIDER_MODELS,
    PROVIDER_OPENAI,
    PROVIDER_OPENAI_COMPATIBLE,
    STATUS_CONFIGURED,
    STATUS_CONNECTED,
    STATUS_COMING_SOON,
    STATUS_FAILED,
    STATUS_NOT_CONFIGURED,
    STATUS_NOT_SUPPORTED,
    SUPPORTED_PROVIDERS,
    build_ai_request_debug,
    call_ai_reply,
    classify_error,
    get_default_model,
    is_provider_available,
    mask_sensitive_text,
    normalize_openai_compatible_endpoint_path,
    provider_requires_base_url,
    resolve_model,
    validate_config,
)

st.set_page_config(
    page_title="Buildway AI Core",
    page_icon="🤖",
    layout="wide",
)

# ──────────────────────────────────────────────
# UI Dictionary (i18n skeleton)
# ──────────────────────────────────────────────
LABELS = {
    "繁體中文": {
        "nav_home": "主頁",
        "nav_tenant": "Tenant 設定",
        "nav_ai": "AI Model 設定",
        "nav_db": "Database 設定",
        "nav_kb": "Knowledge Base",
        "nav_crm": "CRM",
        "nav_logs": "Usage Logs",
        "login_title": "Client Login Portal",
        "login_email": "Email",
        "login_password": "Password",
        "login_btn": "登入",
        "login_forgot": "忘記密碼？",
        "login_coming": "登入功能將於 Phase 0.4 推出。",
        "login_demo_note": "Demo 模式：無需登入。",
        "company_name": "Company Name",
        "industry": "Industry",
        "contact_email": "Contact Email",
        "channel": "Default Channel",
        "save_profile": "儲存 Tenant 資料",
        "ai_provider": "AI Provider",
        "model_name": "Model Name",
        "api_key": "API Key",
        "base_url": "Base URL",
        "save_ai": "儲存 AI 設定",
        "db_mode": "Database 模式",
        "db_hosted": "Buildway Hosted",
        "db_client": "Client Existing Database API",
        "db_url": "Database URL",
        "service_key": "API Key / Service Key",
        "readonly_ep": "Read-only API Endpoint（選填）",
        "notes": "備註",
        "qdrant_url": "Qdrant URL",
        "qdrant_key": "Qdrant API Key",
        "collection": "Collection Name",
        "save_db": "儲存 Database 設定",
        "customer_ref": "Customer Ref",
        "customer_msg": "Customer Message",
        "save_session": "儲存 Customer Session",
        "cost_model_title": "SaaS Cost Model",
        "platform_summary": "Platform Summary",
    },
    "简体中文": {
        "nav_home": "主页",
        "nav_tenant": "Tenant 设置",
        "nav_ai": "AI Model 设置",
        "nav_db": "Database 设置",
        "nav_kb": "Knowledge Base",
        "nav_crm": "CRM",
        "nav_logs": "Usage Logs",
        "login_title": "Client Login Portal",
        "login_email": "Email",
        "login_password": "Password",
        "login_btn": "登录",
        "login_forgot": "忘记密码？",
        "login_coming": "登录功能将于 Phase 0.4 推出。",
        "login_demo_note": "Demo 模式：无需登录。",
        "company_name": "Company Name",
        "industry": "Industry",
        "contact_email": "Contact Email",
        "channel": "Default Channel",
        "save_profile": "保存 Tenant 资料",
        "ai_provider": "AI Provider",
        "model_name": "Model Name",
        "api_key": "API Key",
        "base_url": "Base URL",
        "save_ai": "保存 AI 设置",
        "db_mode": "Database 模式",
        "db_hosted": "Buildway Hosted",
        "db_client": "Client Existing Database API",
        "db_url": "Database URL",
        "service_key": "API Key / Service Key",
        "readonly_ep": "Read-only API Endpoint（选填）",
        "notes": "备注",
        "qdrant_url": "Qdrant URL",
        "qdrant_key": "Qdrant API Key",
        "collection": "Collection Name",
        "save_db": "保存 Database 设置",
        "customer_ref": "Customer Ref",
        "customer_msg": "Customer Message",
        "save_session": "保存 Customer Session",
        "cost_model_title": "SaaS Cost Model",
        "platform_summary": "Platform Summary",
    },
    "English": {
        "nav_home": "Home",
        "nav_tenant": "Tenant Setup",
        "nav_ai": "AI Model Setup",
        "nav_db": "Database Setup",
        "nav_kb": "Knowledge Base",
        "nav_crm": "CRM Demo",
        "nav_logs": "Usage Logs",
        "login_title": "Client Login Portal",
        "login_email": "Email",
        "login_password": "Password",
        "login_btn": "Login",
        "login_forgot": "Forgot password?",
        "login_coming": "Authentication system coming in Phase 0.4.",
        "login_demo_note": "Demo mode: no login required.",
        "company_name": "Company Name",
        "industry": "Industry",
        "contact_email": "Contact Email",
        "channel": "Default Channel",
        "save_profile": "Save Tenant Profile",
        "ai_provider": "AI Provider",
        "model_name": "Model Name",
        "api_key": "API Key",
        "base_url": "Base URL",
        "save_ai": "Save AI Config",
        "db_mode": "Database Mode",
        "db_hosted": "Buildway Hosted",
        "db_client": "Client Existing Database API",
        "db_url": "Database URL",
        "service_key": "API Key / Service Key",
        "readonly_ep": "Read-only API Endpoint (optional)",
        "notes": "Notes",
        "qdrant_url": "Qdrant URL",
        "qdrant_key": "Qdrant API Key",
        "collection": "Collection Name",
        "save_db": "Save Database Config",
        "customer_ref": "Customer Ref",
        "customer_msg": "Customer Message",
        "save_session": "Save Customer Session",
        "cost_model_title": "SaaS Cost Model",
        "platform_summary": "Platform Summary",
    },
}

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "logo.png"

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=120)
    else:
        st.markdown("### Buildway")
    st.markdown("**Buildway Tech (HK) Limited**")
    st.caption("AI Core SaaS Platform")
    st.divider()

    lang = st.selectbox("Language / 語言", ["繁體中文", "简体中文", "English"], index=0)
    L = LABELS[lang]

    st.divider()

    page = st.radio(
        "Navigation",
        [
            L["nav_home"],
            L["nav_tenant"],
            L["nav_ai"],
            L["nav_db"],
            L["nav_kb"],
            L["nav_crm"],
            L["nav_logs"],
        ],
        label_visibility="collapsed",
    )
    
    st.divider()
    
    # Developer Mode Toggle
    dev_mode = st.checkbox("Developer Mode", value=False)
    st.session_state["dev_mode"] = dev_mode
    if dev_mode:
        st.caption("🔧 Debug mode enabled")

# ──────────────────────────────────────────────
# CRM AI helpers (Phase 0.4B) — defined at module level
# ──────────────────────────────────────────────
CRM_SYSTEM_PROMPT = (
    "You are a professional foreign trade sales assistant. "
    "Generate concise and professional English customer replies. "
    "Avoid hallucination. "
    "If information is missing, ask politely for clarification. "
    "Keep replies business-friendly."
)


def _ensure_ai_state_defaults() -> None:
    configs = st.session_state.setdefault("ai_provider_configs", {})
    for provider in SUPPORTED_PROVIDERS:
        configs.setdefault(
            provider,
            {
                "provider": provider,
                "model": get_default_model(provider),
                "custom_model": "",
                "api_key": "",
                "base_url": "",
                "endpoint_path": DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH,
                "connection_status": STATUS_NOT_CONFIGURED
                if is_provider_available(provider)
                else STATUS_COMING_SOON,
            },
        )

    selected_provider = st.session_state.get("ai_provider", PROVIDER_OPENAI)
    if selected_provider not in SUPPORTED_PROVIDERS:
        selected_provider = PROVIDER_OPENAI
    st.session_state["ai_provider"] = selected_provider
    _sync_selected_ai_config(selected_provider)


def _get_provider_config(provider: str) -> AIProviderConfig:
    raw_config = st.session_state["ai_provider_configs"][provider]
    return AIProviderConfig(
        provider=provider,
        model=raw_config.get("resolved_model")
        or resolve_model(
            raw_config.get("model") or get_default_model(provider),
            raw_config.get("custom_model", ""),
        ),
        api_key=raw_config.get("api_key", ""),
        base_url=raw_config.get("base_url", ""),
        endpoint_path=raw_config.get(
            "endpoint_path",
            DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH,
        ),
        connection_status=raw_config.get("connection_status", STATUS_NOT_CONFIGURED),
    )


def _sync_selected_ai_config(provider: str) -> AIProviderConfig:
    config = _get_provider_config(provider)
    st.session_state["ai_provider"] = config.provider
    st.session_state["ai_model"] = config.model
    st.session_state["ai_api_key"] = config.api_key
    st.session_state["ai_base_url"] = config.base_url
    st.session_state["ai_endpoint_path"] = config.endpoint_path
    st.session_state["ai_connection_status"] = config.connection_status
    st.session_state["ai_configured"] = config.connection_status != STATUS_NOT_CONFIGURED
    return config


def _reset_provider_config(provider: str) -> None:
    default_model = get_default_model(provider)
    st.session_state["ai_provider_configs"][provider] = {
        "provider": provider,
        "model": default_model,
        "custom_model": "",
        "resolved_model": default_model if default_model != "custom" else "",
        "api_key": "",
        "base_url": "",
        "endpoint_path": DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH,
        "connection_status": STATUS_NOT_CONFIGURED
        if is_provider_available(provider)
        else STATUS_COMING_SOON,
    }
    _sync_selected_ai_config(provider)


def _format_ai_api_error(exc: Exception) -> str:
    err = mask_sensitive_text(str(exc))
    err_lower = err.lower()
    exc_name = exc.__class__.__name__.lower()
    if "auth" in err_lower or "api_key" in err_lower or "401" in err_lower:
        return f"Invalid API key: {err}"
    if "quota" in err_lower or "insufficient_quota" in err_lower or "billing" in err_lower:
        return f"Quota exceeded: {err}"
    if "timeout" in err_lower or "timed out" in err_lower or "timeout" in exc_name:
        return f"Timeout: {err}"
    if (
        "model" in err_lower
        and ("not found" in err_lower or "unavailable" in err_lower or "does not exist" in err_lower)
    ) or "notfound" in exc_name:
        return f"Model unavailable: {err}"
    return f"Connection failed: {err}"


def _show_ai_debug(debug) -> None:
    """Only show debug in developer mode."""
    if not st.session_state.get("dev_mode", False):
        return
    
    with st.expander("🔧 Developer Debug", expanded=False):
        st.caption("AI request debug")
        debug_data = {
            "function": debug.function_name,
            "method": debug.method,
            "final_endpoint": debug.final_endpoint,
            "provider": debug.provider,
            "model": debug.model,
            "sdk_or_api": debug.sdk_or_api,
        }
        st.json(debug_data)


def _calculate_confidence_fallback(results: list) -> str:
    """
    Fallback confidence calculation if retriever method unavailable.
    
    Args:
        results: Search results from RAG retriever.
    
    Returns:
        "HIGH", "MEDIUM", or "LOW"
    """
    if not results:
        return "LOW"
    
    # Get similarity from first result
    top_result = results[0]
    
    # Try to get similarity, or calculate from distance
    similarity = top_result.get('similarity')
    if similarity is None:
        distance = top_result.get('distance', 1.0)
        similarity = 1.0 - (distance / 2.0)  # ChromaDB cosine distance normalization
    
    if similarity >= 0.85:
        return "HIGH"
    elif similarity >= 0.65:
        return "MEDIUM"
    else:
        return "LOW"


# ──────────────────────────────────────────────
# Page: Home
# ──────────────────────────────────────────────
if page == L["nav_home"]:
    st.title("Buildway AI Core")
    st.caption("Buildway Tech (HK) Limited — Multi-industry AI SaaS Platform")

    # 1. Client Login Portal
    st.subheader(L["login_title"])
    with st.container(border=True):
        st.warning(L["login_coming"])
        st.caption(L["login_demo_note"])
        login_col1, login_col2 = st.columns(2)
        with login_col1:
            st.text_input(L["login_email"], placeholder="admin@yourcompany.com", disabled=True)
        with login_col2:
            st.text_input(L["login_password"], type="password", placeholder="••••••••", disabled=True)
        st.button(L["login_btn"], disabled=True)
        st.markdown(f"_{L['login_forgot']}_")
        st.markdown("""
Coming in Phase 0.4:
- Admin login
- Staff login
- Tenant isolation
- Role-based permission
""")

    st.divider()

    # 2. Platform Summary
    st.subheader(L["platform_summary"])
    st.markdown(
        "Buildway AI Core is a general AI operation platform supporting multiple industry verticals. "
        "Each client runs as an isolated Tenant with their own Knowledge Base, AI Model API key, "
        "and CRM workflow."
    )

    # 3. Core Modules
    st.subheader("Core Modules")
    st.markdown("""
| Module | Path | Description |
|---|---|---|
| Session Memory | `core/memory/base.py` | Tenant-isolated session storage |
| RAG Manager | `core/rag/base.py` | Knowledge Base retrieval |
| Tenant Context | `core/tenant/context.py` | Multi-tenant isolation |
| Config Loader | `core/config.py` | Env-based config (no hardcoded keys) |
| Agent Router | `core/agents/` | Generic agent routing framework |
| Action Manager | `core/actions/` | Action item tracking |
| Report Generator | `core/reports/` | Output generation |
| Workflow Tracker | `core/workflow/` | Workflow step tracking |
""")

    # 4. Verticals
    st.subheader("Verticals")
    st.markdown("""
| Vertical | Path | Status |
|---|---|---|
| CRM | `verticals/crm/` | Active Demo |
| Construction | `verticals/construction/` | Existing vertical |
| Document AI | `verticals/document_ai/` | Placeholder |
| ERP | `verticals/erp/` | Placeholder |
""")

    st.divider()

    # 5. SaaS Cost Model (bottom)
    st.subheader(L["cost_model_title"])
    with st.container(border=True):
        st.markdown("""
**A. Buildway Hosted**
Buildway provides hosting, Tenant database, Vector DB and platform maintenance.
Client pays monthly SaaS fee. Usage beyond included quota may be charged separately.

**B. Client Existing Database API**
Client provides Database / ERP / CRM API. Buildway only connects to client API.
Client keeps full data ownership.

**C. AI Model API**
Client provides OpenAI / Claude / Gemini / DeepSeek API key, or
Buildway can provide managed AI usage as optional paid add-on.

**D. WhatsApp API**
Client owns WhatsApp Business API and Meta account.
Buildway integrates the Webhook and workflow.
""")

# ──────────────────────────────────────────────
# Page: Tenant Setup
# ──────────────────────────────────────────────
elif page == L["nav_tenant"]:
    st.title(L["nav_tenant"])

    with st.form("tenant_form"):
        company_name = st.text_input(L["company_name"], value="Demo Trading Company")
        industry = st.text_input(L["industry"], value="Foreign Trade")
        contact_email = st.text_input(L["contact_email"], value="admin@example.com")
        default_channel = st.selectbox(L["channel"], ["WhatsApp", "Email", "Web Chat"], index=0)
        save_tenant = st.form_submit_button(L["save_profile"])

    if save_tenant:
        st.success(f"{L['save_profile']}: **{company_name}** | {industry} | {default_channel}")
        st.caption("In production, stored in tenants table with unique tenant_id.")

# ──────────────────────────────────────────────
# Page: AI Model Setup
# ──────────────────────────────────────────────
elif page == L["nav_ai"]:
    _ensure_ai_state_defaults()
    st.title(L["nav_ai"])

    st.warning(
        "API keys are stored in session memory only. "
        "Keys are never written to disk, logged, or committed. "
        "Session is cleared when the browser tab is closed."
    )
    st.info(
        "Client-owned API key is recommended to avoid mixed Token billing. "
        "Buildway-managed AI usage can be provided as a paid add-on."
    )
    st.markdown(f"**Available Now:** {', '.join(AVAILABLE_PROVIDERS)}")
    st.markdown(f"**Coming Soon:** {', '.join(COMING_SOON_PROVIDERS)}")

    # Provider selection (outside form so model list updates immediately)
    current_provider = st.session_state.get("ai_provider", PROVIDER_OPENAI)
    provider = st.selectbox(
        L["ai_provider"],
        SUPPORTED_PROVIDERS,
        index=SUPPORTED_PROVIDERS.index(current_provider)
        if current_provider in SUPPORTED_PROVIDERS
        else 0,
        key="ai_provider_select",
    )
    if provider != current_provider:
        if current_provider in SUPPORTED_PROVIDERS:
            _reset_provider_config(current_provider)
        st.session_state["ai_provider"] = provider
        _reset_provider_config(provider)

    provider_config = _sync_selected_ai_config(provider)
    raw_provider_config = st.session_state["ai_provider_configs"][provider]
    provider_models = PROVIDER_MODELS[provider]
    stored_model = raw_provider_config.get("model", get_default_model(provider))
    provider_available = is_provider_available(provider)
    if not provider_available:
        st.info(COMING_SOON_MESSAGE)

    with st.form("ai_model_form"):
        model_name = st.selectbox(
            L["model_name"],
            provider_models,
            index=provider_models.index(stored_model) if stored_model in provider_models else 0,
            disabled=not provider_available,
        )
        custom_model_name = ""
        if model_name == "custom":
            custom_model_name = st.text_input(
                "Custom Model Name",
                value=raw_provider_config.get("custom_model", ""),
                placeholder="Enter model name",
                disabled=not provider_available,
            )
        base_url_input = ""
        endpoint_path_input = DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH
        # Only show base_url/endpoint_path for OpenAI-Compatible
        if provider == PROVIDER_OPENAI_COMPATIBLE:
            base_url_input = st.text_input(
                L["base_url"],
                value=provider_config.base_url,
                placeholder="https://api.example.com/v1",
            )
            endpoint_path_input = st.text_input(
                "Endpoint Path",
                value=provider_config.endpoint_path or DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH,
                placeholder="/chat/completions",
            )
        api_key_input = st.text_input(
            PROVIDER_KEY_LABELS[provider],
            type="password",
            placeholder=PROVIDER_KEY_PLACEHOLDERS[provider],
            disabled=not provider_available,
        )

        save_ai = st.form_submit_button(L["save_ai"], disabled=not provider_available)
        test_ai = st.form_submit_button("Test Connection", disabled=not provider_available)

    next_api_key = api_key_input or provider_config.api_key
    next_base_url = base_url_input if provider_requires_base_url(provider) else ""
    next_endpoint_path = (
        endpoint_path_input
        if provider_requires_base_url(provider)
        else DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH
    )
    resolved_model = resolve_model(model_name, custom_model_name)

    if save_ai or test_ai:
        config_error = False
        if provider_requires_base_url(provider) and not next_base_url:
            st.error("Missing Base URL")
            config_error = True
        elif provider_requires_base_url(provider):
            try:
                next_endpoint_path = normalize_openai_compatible_endpoint_path(next_endpoint_path)
            except ValueError as exc:
                st.error(str(exc))
                next_endpoint_path = ""
                config_error = True
        if config_error:
            pass
        elif not next_api_key:
            st.error("Missing API key")
        elif not resolved_model:
            st.error("Missing Model Name")
        else:
            st.session_state["ai_provider_configs"][provider] = {
                "provider": provider,
                "model": model_name,
                "custom_model": custom_model_name,
                "resolved_model": resolved_model,
                "api_key": next_api_key,
                "base_url": next_base_url,
                "endpoint_path": next_endpoint_path,
                "connection_status": STATUS_CONFIGURED,
            }
            provider_config = _sync_selected_ai_config(provider)
            if save_ai:
                st.success(f"{provider} configured - model: `{resolved_model}`")
                st.caption("Run Test Connection before using this provider in CRM.")

    if test_ai and provider_config.configured:
        debug = build_ai_request_debug(
            provider_config.provider,
            provider_config.model,
            provider_config.base_url,
            provider_config.endpoint_path,
        )
        _show_ai_debug(debug)
        validation_result = validate_config(provider_config)
        with st.spinner("Testing AI provider connection..."):
            if validation_result:
                result = validation_result
            else:
                try:
                    ai_result = call_ai_reply(
                        provider=provider_config.provider,
                        message="Reply with OK only.",
                        api_key=provider_config.api_key,
                        model=provider_config.model,
                        base_url=provider_config.base_url,
                        endpoint_path=provider_config.endpoint_path,
                        test_mode=True,
                    )
                    _show_ai_debug(ai_result.debug)
                    result = (
                        ConnectionResult(STATUS_CONNECTED, "Connection successful.")
                        if "OK" in ai_result.content.upper() or ai_result.content.strip()
                        else ConnectionResult(STATUS_FAILED, "Connection failed: empty response")
                    )
                except OpenAICompatibleRequestError as exc:
                    result = exc.result
                except Exception as exc:
                    result = classify_error(exc)
        st.session_state["ai_provider_configs"][provider]["connection_status"] = result.status
        provider_config = _sync_selected_ai_config(provider)
        if result.status == STATUS_CONNECTED:
            st.success(result.message)
        elif result.status == STATUS_NOT_CONFIGURED:
            st.error(result.message)
        elif result.status in {STATUS_COMING_SOON, STATUS_NOT_SUPPORTED}:
            st.info(result.message)
        else:
            st.error(result.message)

    st.divider()
    provider_config = _sync_selected_ai_config(provider)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(L["ai_provider"], provider_config.provider)
    with c2:
        st.metric(L["model_name"], provider_config.model or "Not set")
    with c3:
        st.metric("Connection Status", provider_config.connection_status)
    if provider_requires_base_url(provider):
        st.caption(f"Base URL: `{provider_config.base_url or 'Not set'}`")
        st.caption(f"Endpoint Path: `{provider_config.endpoint_path or DEFAULT_OPENAI_COMPATIBLE_ENDPOINT_PATH}`")

# ──────────────────────────────────────────────
# Page: Database Setup
# ──────────────────────────────────────────────
elif page == L["nav_db"]:
    st.title(L["nav_db"])

    st.warning(
        "API keys are not stored in this demo version. "
        "Production version will store encrypted keys in a secure backend."
    )

    st.subheader(L["db_mode"])
    db_mode = st.radio(
        "Choose database mode:",
        [L["db_hosted"], L["db_client"]],
        index=0,
        label_visibility="collapsed",
    )

    if db_mode == L["db_hosted"]:
        st.info(
            f"**{L['db_hosted']}** — No external Database is required from client. "
            "Database / Vector DB / storage are provided under Buildway SaaS plan."
        )
        st.caption("Cost responsibility: included in monthly SaaS plan / subject to quota.")
        st.markdown(
            "> Client does not need to prepare a database server. "
            "Client still needs to prepare business data such as FAQ, product catalog and reply templates."
        )
    else:
        st.caption("Connect your existing Database API.")

        with st.form("db_form"):
            db_provider = st.selectbox(
                "Database Provider",
                ["Supabase", "PostgreSQL", "Firebase", "Custom REST API"],
            )
            db_url = st.text_input(
                L["db_url"],
                placeholder="https://xxxx.supabase.co or postgresql://...",
            )
            db_service_key = st.text_input(
                L["service_key"],
                type="password",
                placeholder="(never stored or committed)",
            )
            db_readonly_endpoint = st.text_input(
                L["readonly_ep"],
                placeholder="https://xxxx.supabase.co/rest/v1",
            )
            db_notes = st.text_area(L["notes"], placeholder="e.g. project name, region", height=60)

            st.divider()
            st.markdown("**Vector Database (Qdrant)**")
            qdrant_url = st.text_input(
                L["qdrant_url"],
                placeholder="https://your-qdrant-instance.com or http://localhost:6333",
            )
            qdrant_api_key = st.text_input(
                L["qdrant_key"],
                type="password",
                placeholder="(never stored or committed)",
            )
            collection_name = st.text_input(L["collection"], value="crm_knowledge_base")
            save_db = st.form_submit_button(L["save_db"])

        if save_db:
            if db_url or qdrant_url:
                st.success(f"{L['save_db']} (demo — not stored anywhere).")
                if db_url:
                    st.info(f"DB: `{db_provider}` — URL configured")
                if qdrant_url:
                    st.info(f"Qdrant: collection `{collection_name}` — URL configured")
            else:
                st.warning("No Database URL provided. Using placeholder mode.")

# ──────────────────────────────────────────────
# Page: Knowledge Base (Phase 0.4D — Real RAG)
# ──────────────────────────────────────────────
elif page == L["nav_kb"]:
    st.title(L["nav_kb"])
    
    # Initialize RAG retriever in session state
    if "rag_retriever" not in st.session_state:
        try:
            from core.rag.retriever import RAGRetriever
            from core.rag.embedder import PROVIDER_LOCAL
            from pathlib import Path
            
            # Use local embeddings by default
            st.session_state["rag_retriever"] = RAGRetriever(
                embedding_provider=PROVIDER_LOCAL,
            )
            st.session_state["rag_initialized"] = True
        except Exception as e:
            st.session_state["rag_initialized"] = False
            st.session_state["rag_error"] = str(e)
    
    # KB Statistics
    if st.session_state.get("rag_initialized"):
        try:
            stats = st.session_state["rag_retriever"].get_stats()
            kb_col1, kb_col2, kb_col3 = st.columns(3)
            with kb_col1:
                st.metric("Total Chunks", stats["total_chunks"])
            with kb_col2:
                st.metric("Embedding Provider", stats["embedding_provider"].replace("Embedder", ""))
            with kb_col3:
                st.metric("Status", "Ready" if stats["total_chunks"] > 0 else "Empty")
        except Exception as e:
            st.error(f"Failed to load KB stats: {e}")
    else:
        st.error(f"RAG system not initialized: {st.session_state.get('rag_error', 'Unknown error')}")
        st.info("Please check that chromadb and sentence-transformers are installed.")
    
    st.divider()
    
    # Upload Section
    st.subheader("Upload Documents")
    st.caption("Supported formats: PDF, TXT, DOCX, MD, CSV")
    
    uploaded_files = st.file_uploader(
        "Upload Knowledge Base Documents",
        type=["pdf", "txt", "docx", "md", "csv"],
        accept_multiple_files=True,
        key="kb_uploader",
    )
    
    if uploaded_files and st.session_state.get("rag_initialized"):
        if st.button("Index Uploaded Files", type="primary", key="index_files_btn"):
            from pathlib import Path
            import tempfile
            import traceback
            
            st.write("🔄 Starting indexing workflow...")
            st.write(f"📁 Files to process: {len(uploaded_files)}")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            indexed_count = 0
            failed_count = 0
            
            with st.spinner("Indexing documents..."):
                for i, uploaded_file in enumerate(uploaded_files):
                    try:
                        st.write(f"📄 Indexing: **{uploaded_file.name}**")
                        status_text.text(f"Processing {uploaded_file.name}...")
                        
                        # Save to temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = Path(tmp_file.name)
                        
                        st.write(f"  → Temp file: {tmp_path}")
                        
                        # Index document
                        st.write(f"  → Calling index_document()...")
                        result = st.session_state["rag_retriever"].index_document(
                            file_path=tmp_path,
                            metadata={"source": "upload", "original_name": uploaded_file.name},
                        )
                        
                        st.write(f"  → Result: {result}")
                        
                        # Clean up temp file
                        tmp_path.unlink()
                        
                        st.success(f"✓ {uploaded_file.name}: {result['chunk_count']} chunks indexed")
                        indexed_count += 1
                        
                    except Exception as e:
                        failed_count += 1
                        error_detail = traceback.format_exc()
                        st.error(f"✗ {uploaded_file.name}: {str(e)}")
                        with st.expander("Error Details"):
                            st.code(error_detail)
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text("Indexing complete!")
                st.write(f"✅ Indexed: {indexed_count} | ❌ Failed: {failed_count}")
                
                if indexed_count > 0:
                    st.info("Refreshing page to update stats...")
                    st.rerun()
    
    st.divider()
    
    # Indexed Documents List
    st.subheader("Indexed Documents")
    
    if st.session_state.get("rag_initialized"):
        try:
            stats = st.session_state["rag_retriever"].get_stats()
            documents = st.session_state["rag_retriever"].list_documents()
            
            if stats["total_chunks"] == 0:
                st.info("No documents indexed yet. Upload documents above to get started.")
            else:
                st.caption(f"Total chunks in vector database: {stats['total_chunks']}")
                
                # Document list with management buttons
                for doc in documents:
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 2, 1, 1])
                    with col1:
                        st.write(f"📄 **{doc['file_name']}**")
                    with col2:
                        st.write(f"{doc['chunk_count']} chunks")
                    with col3:
                        indexed_time = doc['indexed_at'][:19].replace('T', ' ') if doc['indexed_at'] else ""
                        st.caption(indexed_time)
                    with col4:
                        if st.button("🗑️", key=f"del_{doc['file_name']}", help="Delete document"):
                            try:
                                deleted = st.session_state["rag_retriever"].delete_document(doc['file_name'])
                                st.success(f"Deleted {deleted} chunks from {doc['file_name']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {e}")
                    with col5:
                        st.button("🔄", key=f"reindex_{doc['file_name']}", help="Re-index (requires original file)", disabled=True)
                
                st.divider()
                
                # Clear all button
                if st.button("Clear All Documents", type="secondary"):
                    if st.button("Confirm Clear All", type="secondary", key="confirm_clear_all"):
                        st.session_state["rag_retriever"].clear_all()
                        st.success("All documents cleared from vector database.")
                        st.rerun()
        except Exception as e:
            st.error(f"Failed to load documents: {e}")
    
    st.divider()
    
    # KB Search Test Box
    st.subheader("Search Knowledge Base")
    
    if st.session_state.get("rag_initialized"):
        search_col1, search_col2 = st.columns([4, 1])
        with search_col1:
            search_query = st.text_input("Search query", placeholder="e.g., What is MOQ?", key="kb_search_query")
        with search_col2:
            top_k = st.number_input("Top K", min_value=1, max_value=10, value=5, key="kb_search_top_k")
        
        if st.button("Search KB", key="kb_search_btn"):
            if search_query:
                try:
                    with st.spinner("Searching..."):
                        results = st.session_state["rag_retriever"].search(search_query, top_k=top_k)
                    
                    if results:
                        st.success(f"Found {len(results)} results")
                        for i, result in enumerate(results, 1):
                            filename = result['metadata'].get('file_name', 'unknown')
                            distance = result.get('distance', 0.0)
                            with st.expander(f"Result {i} — {filename} (distance: {distance:.4f})"):
                                preview = result['text'][:500]
                                if len(result['text']) > 500:
                                    preview += "..."
                                st.write(preview)
                                st.caption(f"Chunk index: {result['metadata'].get('chunk_index', 'N/A')}")
                    else:
                        st.info("No results found")
                except Exception as e:
                    st.error(f"Search failed: {e}")
            else:
                st.warning("Please enter a search query")
    else:
        st.info("RAG system not initialized. Please check Knowledge Base setup.")
    
    st.divider()
    
    # FAQ Data Template (keep existing)
    with st.expander("📋 FAQ Data Template Reference"):
        st.markdown(
            "Prepare your FAQ as an Excel or CSV file with the following columns. "
            "This is the recommended format for building the RAG Knowledge Base."
        )
        st.markdown("""
| Column | Description |
|---|---|
| Category | Topic group, e.g. MOQ, Shipping, Payment |
| Question | Customer question text |
| Standard Answer | Approved reply for this question |
| Can Auto Reply | Yes / No — whether AI can reply without human review |
| Need Human Approval | Yes / No — whether staff must approve before sending |
| Risk Level | Low / Medium / High |
| Notes | Internal notes, e.g. "Do not quote exact price" |
""")

# ──────────────────────────────────────────────
# Page: CRM Demo  (Phase 0.4B — Real AI API)
# ──────────────────────────────────────────────
elif page == L["nav_crm"]:

    # ── Session state init ────────────────────────
    _ensure_ai_state_defaults()
    
    # Backward compatibility: migrate crm_message to customer_message
    if "customer_message" not in st.session_state:
        st.session_state["customer_message"] = st.session_state.get("crm_message", "")
    
    if "crm_reply" not in st.session_state:
        st.session_state["crm_reply"] = ""
    if "crm_reply_source" not in st.session_state:
        st.session_state["crm_reply_source"] = ""
    if "crm_kb_context_used" not in st.session_state:
        st.session_state["crm_kb_context_used"] = False

    st.title("CRM AI Assist")
    st.caption(
        "Tenant: Demo Trading Company  |  Industry: Foreign Trade  |  Channel: WhatsApp"
    )

    # ── AI status banner ──────────────────────────
    selected_config = _sync_selected_ai_config(st.session_state.get("ai_provider", PROVIDER_OPENAI))
    ai_connected = selected_config.connection_status == STATUS_CONNECTED
    st.subheader("Current AI Status")
    status_col1, status_col2, status_col3 = st.columns(3)
    with status_col1:
        st.metric("Provider", selected_config.provider)
    with status_col2:
        st.metric("Model", selected_config.model or "Not set")
    with status_col3:
        st.metric("Connection Status", selected_config.connection_status)
    if ai_connected:
        st.success(
            f"AI Provider connected: **{st.session_state.get('ai_provider')}** — "
            f"`{selected_config.model}`"
        )
    elif selected_config.connection_status in {STATUS_COMING_SOON, STATUS_NOT_SUPPORTED}:
        st.info(CRM_PROVIDER_UNAVAILABLE_MESSAGE)
    elif selected_config.connection_status == STATUS_NOT_CONFIGURED:
        st.warning("No AI model configured. Please complete AI Model Setup first.")
    else:
        st.warning(CONNECTION_REQUIRED_MESSAGE)

    # ── Customer message input ────────────────────
    st.subheader("Customer Message")
    customer_input = st.text_area(
        "Customer Message",
        key="customer_message",
        height=200,
        label_visibility="collapsed",
        placeholder="Paste customer inquiry here...",
    )

    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        generate_clicked = st.button(
            "Generate Draft Reply",
            type="primary",
            use_container_width=True,
            disabled=not ai_connected,
        )
    with btn_col2:
        clear_clicked = st.button("Clear", use_container_width=True)

    if clear_clicked:
        st.session_state["customer_message"] = ""
        st.session_state["crm_reply"] = ""
        st.session_state["crm_reply_source"] = ""
        st.session_state["crm_kb_context_used"] = False
        st.session_state["crm_confidence"] = "N/A"
        st.session_state["crm_conflict_warning"] = None
        st.session_state["crm_last_kb_results"] = []

    if generate_clicked:
        if not st.session_state["customer_message"].strip():
            st.warning("Please enter a customer message before generating.")
        else:
            selected_config = _sync_selected_ai_config(st.session_state.get("ai_provider", PROVIDER_OPENAI))
            if selected_config.connection_status == STATUS_CONNECTED:
                _show_ai_debug(
                    build_ai_request_debug(
                        selected_config.provider,
                        selected_config.model,
                        selected_config.base_url,
                        selected_config.endpoint_path,
                    )
                )
                with st.spinner("Generating AI draft..."):
                    try:
                        # Phase 0.5A: RAG retrieval with guardrails
                        kb_context = ""
                        kb_used = False
                        kb_results = []
                        confidence_level = "LOW"
                        conflict_warning = None
                        
                        if st.session_state.get("rag_initialized"):
                            try:
                                retriever = st.session_state["rag_retriever"]
                                results = retriever.search(st.session_state["customer_message"], top_k=5)
                                
                                if results:
                                    kb_used = True
                                    kb_results = results  # Store for display
                                    
                                    # Calculate confidence with fallback
                                    try:
                                        if hasattr(retriever, 'calculate_confidence'):
                                            confidence_level = retriever.calculate_confidence(results)
                                        else:
                                            confidence_level = _calculate_confidence_fallback(results)
                                    except Exception:
                                        confidence_level = _calculate_confidence_fallback(results)
                                    
                                    # Detect conflicts with fallback
                                    try:
                                        if hasattr(retriever, 'detect_conflicts'):
                                            conflict_warning = retriever.detect_conflicts(results, st.session_state["customer_message"])
                                        else:
                                            conflict_warning = None
                                    except Exception:
                                        conflict_warning = None
                                    
                                    # Build context
                                    context_parts = []
                                    for i, result in enumerate(results, 1):
                                        context_parts.append(f"[Context {i}]\n{result['text']}")
                                    kb_context = "\n\n".join(context_parts)
                            except Exception as kb_error:
                                st.caption(f"KB retrieval failed (continuing without context): {kb_error}")
                        
                        # Store KB results and metadata in session state
                        st.session_state["crm_last_kb_results"] = kb_results
                        st.session_state["crm_confidence"] = confidence_level
                        st.session_state["crm_conflict_warning"] = conflict_warning
                        
                        # Build system prompt with anti-hallucination guardrails
                        system_prompt = CRM_SYSTEM_PROMPT
                        if kb_context:
                            system_prompt = """You are a professional foreign trade sales assistant.

STRICT RULES:
- NEVER invent pricing information
- NEVER invent shipping fees or delivery times
- NEVER invent MOQ (Minimum Order Quantity)
- NEVER make up product specifications
- ONLY use information from the provided Knowledge Base context
- If information is missing: politely ask follow-up questions
- If confidence is low: explicitly state uncertainty
- If KB has conflicting data: explain the conflict instead of choosing randomly
- Do not estimate numerical values if exact information is unavailable

CONTEXT (from Knowledge Base):
{kb_context}

Generate a professional reply based ONLY on the customer message and context above.
If the answer is not in the knowledge base, say so and ask for clarification.""".format(kb_context=kb_context)
                        
                        ai_result = call_ai_reply(
                            provider=selected_config.provider,
                            message=customer_input,
                            api_key=selected_config.api_key,
                            model=selected_config.model,
                            base_url=selected_config.base_url,
                            endpoint_path=selected_config.endpoint_path,
                            system_prompt=system_prompt,
                        )
                        _show_ai_debug(ai_result.debug)
                        reply = ai_result.content
                        if reply:
                            st.session_state["crm_reply"] = reply
                            # Provider-specific source labels
                            provider_source_map = {
                                "OpenAI": "OpenAI API",
                                "Claude": "Claude API",
                                "Gemini": "Gemini API",
                                "DeepSeek": "DeepSeek API",
                                "OpenAI-Compatible": "OpenAI-Compatible API",
                            }
                            st.session_state["crm_reply_source"] = provider_source_map.get(
                                selected_config.provider, f"{selected_config.provider} API"
                            )
                            st.session_state["crm_kb_context_used"] = kb_used
                        else:
                            st.error("AI returned an empty response. Please try again.")
                    except Exception as e:
                        st.error(_format_ai_api_error(e))
            elif selected_config.connection_status in {STATUS_COMING_SOON, STATUS_NOT_SUPPORTED}:
                st.session_state["crm_reply"] = ""
                st.session_state["crm_reply_source"] = ""
                st.info(CRM_PROVIDER_UNAVAILABLE_MESSAGE)
            else:
                st.session_state["crm_reply"] = ""
                st.session_state["crm_reply_source"] = ""
                st.error(CONNECTION_REQUIRED_MESSAGE)

    # ── Draft reply output panel ──────────────────
    if st.session_state["crm_reply"]:
        st.divider()
        st.subheader("Draft Reply")

        with st.container(border=True):
            st.markdown(
                "<div style='font-family: Arial, sans-serif; font-size: 14px; "
                "line-height: 1.8; white-space: pre-wrap; padding: 4px 0;'>"
                + st.session_state["crm_reply"].replace("\n", "<br>")
                + "</div>",
                unsafe_allow_html=True,
            )

        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        with action_col1:
            src = st.session_state.get("crm_reply_source", "")
            st.caption(f"Source: {src}" if src else "")
        with action_col2:
            kb_used = st.session_state.get("crm_kb_context_used", False)
            st.caption(f"KB Context: {'Yes ✓' if kb_used else 'No'}")
        with action_col3:
            confidence = st.session_state.get("crm_confidence", "N/A")
            confidence_emoji = {
                "HIGH": "🟢",
                "MEDIUM": "🟡",
                "LOW": "🔴"
            }.get(confidence, "⚪")
            st.caption(f"Confidence: {confidence_emoji} {confidence}")
        with action_col4:
            if st.button("Copy Reply", use_container_width=True):
                st.toast("Reply copied (browser clipboard integration coming in Phase 0.5).")
        
        # Conflict Warning Display
        if st.session_state.get("crm_conflict_warning"):
            st.warning(st.session_state["crm_conflict_warning"])
        
        # Retrieved KB Context Display (Phase 0.5A with debug info)
        if st.session_state.get("crm_last_kb_results"):
            with st.expander("📚 Retrieved KB Context (Debug)"):
                for i, result in enumerate(st.session_state["crm_last_kb_results"], 1):
                    filename = result['metadata'].get('file_name', 'unknown')
                    distance = result.get('distance', 0.0)
                    similarity = result.get('similarity', 0.0)
                    source_weight = result.get('source_weight', 1.0)
                    weighted_score = result.get('weighted_score', 0.0)
                    chunk_index = result['metadata'].get('chunk_index', 'N/A')
                    
                    st.markdown("---")
                    st.caption(f"**Source {i}:** {filename}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Similarity", f"{similarity:.3f}")
                    with col2:
                        st.metric("Weight", f"{source_weight:.2f}x")
                    with col3:
                        st.metric("Final Score", f"{weighted_score:.3f}")
                    
                    st.caption(f"Chunk #{chunk_index}")
                    
                    preview = result['text'][:500]
                    if len(result['text']) > 500:
                        preview += "..."
                    st.write(preview)

    st.divider()

    # ── Customer memory panel ─────────────────────
    st.subheader("Customer Memory")
    mem_col1, mem_col2, mem_col3 = st.columns(3)
    with mem_col1:
        st.text_area("Customer Summary", value="(Not connected)", height=80, disabled=True)
    with mem_col2:
        st.text_area("Last Inquiry", value="(Not connected)", height=80, disabled=True)
    with mem_col3:
        st.text_area("Follow-up Status", value="(Not connected)", height=80, disabled=True)
    st.caption("Customer memory will be stored per tenant_id in Supabase in Phase 1.")

    st.divider()

    # ── Save session ──────────────────────────────
    st.subheader(L["save_session"])
    with st.form("session_form"):
        customer_ref = st.text_input(L["customer_ref"], value="CUST-001")
        customer_message_save = st.text_input(
            L["customer_msg"],
            value=st.session_state.get("crm_message", "What is your MOQ?"),
        )
        submitted = st.form_submit_button(L["save_session"])

    if submitted:
        try:
            from core.memory.session_memory import save_session, load_sessions
            sid = save_session(
                project_ref=customer_ref,
                file_names=[],
                file_types=[],
                selected_agents=["crm_agent"],
                risk_level="low",
                analysis_summary="CRM demo session.",
                question=customer_message_save,
            )
            st.success(f"Session saved: `{sid}`")
            sessions = load_sessions(project_ref=customer_ref)
            st.write(f"Total sessions for `{customer_ref}`: {len(sessions)}")
            if sessions:
                st.json(sessions[0])
        except Exception as e:
            st.warning(f"Session memory not connected (expected in skeleton): {e}")
            st.info(
                f"Would save: customer_ref=`{customer_ref}`, "
                f"message=`{customer_message_save}`"
            )

# ──────────────────────────────────────────────
# Page: Usage Logs
# ──────────────────────────────────────────────
elif page == L["nav_logs"]:
    st.title(L["nav_logs"])
    st.info("Usage logs will be populated once AI Model is connected.")

    import pandas as pd
    st.dataframe(
        pd.DataFrame({
            "Date": ["—", "—", "—"],
            "Tenant": ["Demo Trading Company", "—", "—"],
            "Provider": ["OpenAI", "—", "—"],
            "Tokens Used": [0, 0, 0],
            "Estimated Cost (USD)": [0.00, 0.00, 0.00],
        }),
        use_container_width=True,
    )
    st.caption(
        "In production, usage_logs table in Supabase tracks all API calls per tenant_id."
    )
