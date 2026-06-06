"""
apps/streamlit_admin/app.py
---------------------------
Buildway AI Core — Admin Dashboard (Phase 0.2 skeleton)
Minimal Streamlit UI for operator overview.
"""

import sys
import os

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Buildway AI Core — Admin",
    page_icon="🏗️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🏗️ Buildway AI Core")
st.caption("Admin Dashboard — Phase 0.2 Skeleton")
st.divider()

# ---------------------------------------------------------------------------
# Sidebar — navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select section",
        ["Overview", "Tenants", "Knowledge Bases", "API Keys", "Usage Logs"],
        index=0,
    )

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.subheader("System Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tenants", "—", help="Total registered tenants")
    with col2:
        st.metric("Active Sessions", "—", help="Open chat sessions today")
    with col3:
        st.metric("Messages Today", "—", help="Messages processed today")
    with col4:
        st.metric("Pending Actions", "—", help="Action items awaiting review")

    st.info("ℹ️ Connect to Supabase in Phase 2 to populate live metrics.")

# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------
elif page == "Tenants":
    st.subheader("Tenant List")
    st.warning("⚠️ Placeholder — tenant data will be loaded from Supabase in Phase 2.")

    # Sample placeholder table
    sample_tenants = [
        {"ID": "—", "Name": "Demo Tenant A", "Industry": "CRM", "Status": "trial"},
        {"ID": "—", "Name": "Demo Tenant B", "Industry": "Construction", "Status": "active"},
    ]
    st.dataframe(sample_tenants, use_container_width=True)

    st.button("＋ Add Tenant", disabled=True, help="Available in Phase 2")

# ---------------------------------------------------------------------------
# Knowledge Bases
# ---------------------------------------------------------------------------
elif page == "Knowledge Bases":
    st.subheader("Knowledge Bases")
    st.warning("⚠️ Placeholder — knowledge base management available in Phase 2.")

    st.markdown("""
    Each tenant has one or more knowledge bases:
    - **FAQ** — Common questions and answers
    - **Product Catalog** — Products and pricing
    - **SOP** — Standard operating procedures
    - **Custom** — Any other documents
    """)

    st.button("＋ Upload Document", disabled=True, help="Available in Phase 2")

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
elif page == "API Keys":
    st.subheader("API Key Status")
    st.warning("⚠️ Placeholder — API key management available in Phase 2.")

    st.markdown("""
    Tenants supply their own API keys:
    | Provider | Status |
    |---|---|
    | OpenAI | Not configured |
    | Anthropic | Not configured |
    | WhatsApp Business API | Not configured |
    """)

    st.info("🔒 API keys are stored encrypted. Real values are never displayed here.")

# ---------------------------------------------------------------------------
# Usage Logs
# ---------------------------------------------------------------------------
elif page == "Usage Logs":
    st.subheader("Usage Logs")
    st.warning("⚠️ Placeholder — usage tracking available in Phase 2.")

    st.markdown("""
    Usage logs track token consumption per tenant:
    - Provider (OpenAI / Anthropic)
    - Tokens used
    - Estimated cost (USD)
    - Timestamp
    """)

    st.info("💡 Token costs are the tenant's responsibility. Buildway does not absorb AI costs.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption("Buildway Tech (HK) Limited — Internal use | Phase 0.2 Skeleton")
