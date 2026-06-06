"""
Buildway AI Core - Group Training MVP.

Run with:
    streamlit run apps/streamlit_group_training/app.py
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st
import altair as alt

from apps.streamlit_group_training.i18n.loader import DEFAULT_LOCALE, SUPPORTED_LOCALES, translate
from apps.streamlit_group_training.services.ocr_service import (
    convert_ocr_text_to_structured_data,
    extract_text_from_image,
)
from verticals.group_training.agents.closing_agent import calculate_hidden_closing_score
from verticals.group_training.agents.training_agent import review_daily_performance
from verticals.group_training.models import CustomerStage, UserRole
from verticals.group_training.models import User, new_id
from verticals.group_training.services.auth_service import AuthService
from verticals.group_training.services.auth_service import hash_password
from verticals.group_training.services.customer_service import CustomerService
from verticals.group_training.services.daily_log_service import DailyLogService
from verticals.group_training.services.dashboard_service import DashboardService
from verticals.group_training.services.sqlite_repository import (
    DEFAULT_TEAM_ID,
    DEFAULT_TENANT_ID,
    SQLiteGroupTrainingRepository,
    default_sqlite_path,
)


TENANT_ID = DEFAULT_TENANT_ID
RAW_I18N_PREFIXES = ("nav.", "schedule.", "training.", "dashboard.", "risk.", "scoring_basis.", "scoring.", "ocr.")


def t(locale: str, key: str, **kwargs) -> str:
    return translate(locale, key, **kwargs)


def is_raw_i18n_key(value: str) -> bool:
    return value.strip().startswith(RAW_I18N_PREFIXES)


def translate_stored_text(locale: str, value: str, fallback_key: str = "") -> str:
    text = (value or "").strip()
    if not text:
        return t(locale, fallback_key) if fallback_key else ""
    if is_raw_i18n_key(text):
        if text == "training.summary_template":
            return t(locale, "training.summary_missing_log")
        return t(locale, text)
    return text


def translated_stage(locale: str, stage: str) -> str:
    return t(locale, f"stage.{stage}")


def translated_role(locale: str, role: UserRole) -> str:
    return t(locale, f"role.{role.value}")


def translated_risk(locale: str, risk_level: str) -> str:
    risk = (risk_level or "").strip()
    if risk.startswith("risk."):
        risk = risk.split(".", 1)[1]
    risk = risk[:1].upper() + risk[1:].lower() if risk else "Low"
    return t(locale, f"risk.{risk}")


def yes_no(locale: str, value: bool) -> str:
    return t(locale, "common.yes" if value else "common.no")


def parse_iso_date_or_today(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


def combine_notes(*parts: str) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


def developer_mode_enabled() -> bool:
    return os.environ.get("BUILDWAY_GROUP_TRAINING_DEVELOPER_MODE", "").strip().lower() in {"1", "true", "yes"}


def role_from_signup_value(value: str) -> UserRole:
    normalized = value.strip().lower()
    if normalized == UserRole.MANAGER.value.lower():
        return UserRole.MANAGER
    return UserRole.AGENT


def signup_user(
    repo: SQLiteGroupTrainingRepository,
    name: str,
    email: str,
    password: str,
    confirm_password: str,
    role_value: str,
) -> tuple[bool, str]:
    if not name.strip():
        return False, "auth.signup_name_required"
    if not email.strip():
        return False, "auth.signup_email_required"
    if password != confirm_password:
        return False, "auth.signup_password_mismatch"
    if repo.find_user_by_email(TENANT_ID, email):
        return False, "auth.signup_email_exists"
    role = role_from_signup_value(role_value)
    repo.add_user(
        User(
            TENANT_ID,
            new_id("user"),
            name.strip(),
            email.strip().lower(),
            role,
            DEFAULT_TEAM_ID,
            "mgr_001" if role == UserRole.AGENT else None,
            hash_password(password),
        )
    )
    return True, "auth.signup_success"


def request_password_reset(repo: SQLiteGroupTrainingRepository, email: str) -> str:
    if email.strip():
        repo.find_user_by_email(TENANT_ID, email)
    return "auth.reset_request_created"


CSV_IMPORT_COLUMN_ALIASES = {
    "name": "name",
    "姓名": "name",
    "phone": "phone",
    "電話": "phone",
    "stage": "stage",
    "客戶階段": "stage",
    "next_meeting_date": "next_meeting_date",
    "下次會議日期": "next_meeting_date",
    "notes": "notes",
    "備註": "notes",
}


def normalize_import_stage(value: str) -> str:
    normalized = str(value or "").strip().lower()
    stage_map = {
        "cold": "Cold",
        "冷": "Cold",
        "warm": "Warm",
        "暖": "Warm",
        "hot": "Hot",
        "熱": "Hot",
        "proposal": "Proposal",
        "方案": "Proposal",
        "closed": "Closed",
        "已成交": "Closed",
        "lost": "Lost",
        "已流失": "Lost",
    }
    return stage_map.get(normalized, CustomerStage.COLD.value)


def parse_import_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return date.today()


def normalize_customer_import_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    renamed = dataframe.rename(columns={column: CSV_IMPORT_COLUMN_ALIASES.get(str(column).strip(), column) for column in dataframe.columns})
    rows = []
    for _, row in renamed.iterrows():
        raw_name = row.get("name", "")
        name = "" if pd.isna(raw_name) else str(raw_name).strip()
        if not name:
            continue
        raw_phone = row.get("phone", "")
        raw_stage = row.get("stage", "")
        raw_next_meeting_date = row.get("next_meeting_date", "")
        raw_notes = row.get("notes", "")
        rows.append(
            {
                "name": name,
                "phone": "" if pd.isna(raw_phone) else str(raw_phone).strip(),
                "stage": normalize_import_stage("" if pd.isna(raw_stage) else str(raw_stage)),
                "next_meeting_date": parse_import_date("" if pd.isna(raw_next_meeting_date) else str(raw_next_meeting_date)),
                "notes": "" if pd.isna(raw_notes) else str(raw_notes).strip(),
            }
        )
    return pd.DataFrame(rows, columns=["name", "phone", "stage", "next_meeting_date", "notes"])


def import_customers_from_dataframe(
    repo: SQLiteGroupTrainingRepository,
    user,
    dataframe: pd.DataFrame,
    target_agent_id: str | None = None,
) -> int:
    normalized = normalize_customer_import_dataframe(dataframe)
    agents = visible_agents(repo, user)
    if user.role == UserRole.AGENT:
        target_agent = user
    else:
        agent_lookup = {agent.id: agent for agent in agents}
        target_agent = agent_lookup.get(target_agent_id or "")
        if target_agent is None:
            target_agent = agents[0] if agents else user
    service = CustomerService(repo)
    for _, row in normalized.iterrows():
        service.create_customer(
            TENANT_ID,
            target_agent.team_id or DEFAULT_TEAM_ID,
            target_agent.id,
            row["name"],
            row["stage"],
            row["phone"],
            row["notes"],
            row["next_meeting_date"],
        )
    return len(normalized)


def localize_columns(dataframe: pd.DataFrame, locale: str) -> pd.DataFrame:
    return dataframe.rename(columns={column: t(locale, f"column.{column}") for column in dataframe.columns})


def scoring_basis_items(locale: str) -> list[str]:
    return [t(locale, f"scoring_basis.item_{index}") for index in range(1, 7)]


def render_scoring_basis(locale: str) -> None:
    with st.expander(t(locale, "scoring_basis.title")):
        for index, item in enumerate(scoring_basis_items(locale), start=1):
            st.markdown(f"{index}. {item}")
        st.caption(t(locale, "scoring_basis.note"))


def logs_by_agent_and_date(logs) -> dict[tuple[str, date], object]:
    return {(log.agent_id, log.activity_date): log for log in logs}


def advice_key_for_log(log) -> str:
    activity = log.call_count + log.whatsapp_count
    conversion_signal = log.appointment_count + log.meeting_count + (log.closing_count * 3)
    if activity < 10 and conversion_signal < 3:
        return "training.advice.low"
    if log.meeting_count == 0:
        return "training.advice.medium"
    if log.closing_count == 0 and log.meeting_count >= 2:
        return "training.advice.medium"
    return "training.advice.high"


def localized_review_summary(locale: str, log, fallback: str) -> str:
    if not log:
        if is_raw_i18n_key(fallback or ""):
            return translate_stored_text(locale, fallback, "training.summary_missing_log")
        return fallback if locale == "en" else t(locale, "training.summary_missing_log")
    return t(
        locale,
        "training.summary_template",
        total_outreach=log.call_count + log.whatsapp_count,
        calls=log.call_count,
        whatsapp=log.whatsapp_count,
        appointments=log.appointment_count,
        meetings=log.meeting_count,
        closings=log.closing_count,
    )


def localized_review_advice(locale: str, log, risk_level: str, fallback: str) -> str:
    if log:
        return t(locale, advice_key_for_log(log))
    if is_raw_i18n_key(fallback or ""):
        return translate_stored_text(locale, fallback, "training.advice.medium")
    if locale == "en":
        return fallback
    if risk_level == "Low":
        return t(locale, "training.advice.high")
    if risk_level == "Medium":
        return t(locale, "training.advice.medium")
    return t(locale, "training.advice.low")


def schedule_priority_key(stage: CustomerStage) -> str:
    if stage in {CustomerStage.HOT, CustomerStage.PROPOSAL}:
        return "schedule.priority_high"
    if stage == CustomerStage.WARM:
        return "schedule.priority_medium"
    return "schedule.priority_low"


def schedule_sort_rank(stage: CustomerStage) -> int:
    order = {
        CustomerStage.HOT: 0,
        CustomerStage.PROPOSAL: 1,
        CustomerStage.WARM: 3,
        CustomerStage.COLD: 4,
        CustomerStage.LOST: 5,
        CustomerStage.CLOSED: 6,
    }
    return order.get(stage, 99)


def schedule_recommendation_key(customers) -> str:
    if not customers:
        return "schedule.recommendation_no_customers"
    if any(schedule_priority_key(customer.stage) == "schedule.priority_high" for customer in customers):
        return "schedule.recommendation_high_priority"
    return "schedule.recommendation_no_high_priority"


def chart_color_range() -> list[str]:
    return ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#64748b"]


def activity_chart(logs_df: pd.DataFrame, locale: str) -> alt.Chart:
    activity_by_date = logs_df.groupby("date", as_index=False)[
        ["calls", "whatsapp", "appointments", "meetings", "closings"]
    ].sum()
    chart_df = activity_by_date.melt("date", var_name="activity_type", value_name="count")
    label_map = {
        "calls": t(locale, "column.calls"),
        "whatsapp": t(locale, "column.whatsapp"),
        "appointments": t(locale, "column.appointments"),
        "meetings": t(locale, "column.meetings"),
        "closings": t(locale, "column.closings"),
    }
    chart_df["activity_label"] = chart_df["activity_type"].map(label_map)
    label_order = list(label_map.values())
    return (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("date:O", title=None, axis=alt.Axis(labelAngle=0, labelLimit=90)),
            xOffset=alt.XOffset("activity_label:N", sort=label_order),
            y=alt.Y("count:Q", title=None, axis=alt.Axis(grid=True, tickMinStep=1)),
            color=alt.Color(
                "activity_label:N",
                title=None,
                sort=label_order,
                scale=alt.Scale(range=chart_color_range()[:5]),
                legend=alt.Legend(orient="bottom", columns=3),
            ),
            tooltip=[
                alt.Tooltip("date:O", title=t(locale, "column.date")),
                alt.Tooltip("activity_label:N", title=t(locale, "chart.activity_type")),
                alt.Tooltip("count:Q", title=t(locale, "chart.activity_count")),
            ],
        )
        .properties(height=280)
    )


def stage_chart(customers, locale: str) -> alt.Chart:
    stage_order = [translated_stage(locale, stage.value) for stage in CustomerStage]
    stage_df = (
        pd.Series([translated_stage(locale, customer.stage.value) for customer in customers])
        .value_counts()
        .reindex(stage_order, fill_value=0)
        .reset_index()
    )
    stage_df.columns = ["stage", "count"]
    return (
        alt.Chart(stage_df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y("stage:N", title=None, sort=stage_order, axis=alt.Axis(labelAngle=0, labelLimit=120)),
            x=alt.X("count:Q", title=None, scale=alt.Scale(nice=True), axis=alt.Axis(tickMinStep=1)),
            color=alt.Color(
                "stage:N",
                title=None,
                sort=stage_order,
                scale=alt.Scale(range=["#64748b", "#f59e0b", "#ef4444", "#7c3aed", "#16a34a", "#94a3b8"]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("stage:N", title=t(locale, "column.stage")),
                alt.Tooltip("count:Q", title=t(locale, "chart.customer_count")),
            ],
        )
        .properties(height=280)
    )


def hidden_score_risk_key(score: float) -> str:
    if score >= 75:
        return "hidden_score.risk_low"
    if score >= 50:
        return "hidden_score.risk_medium"
    return "hidden_score.risk_high"


def hidden_score_summary(scores_df: pd.DataFrame, locale: str) -> pd.DataFrame:
    if scores_df.empty:
        return pd.DataFrame(columns=["agent_id", "average_hidden_score", "risk_hint"])
    summary_df = scores_df.groupby("agent_id", as_index=False)["hidden_score"].mean()
    summary_df["average_hidden_score"] = summary_df["hidden_score"].round(1)
    summary_df["risk_hint"] = summary_df["average_hidden_score"].apply(lambda score: t(locale, hidden_score_risk_key(score)))
    return summary_df[["agent_id", "average_hidden_score", "risk_hint"]]


def hidden_score_chart(score_summary_df: pd.DataFrame, locale: str) -> alt.Chart:
    return (
        alt.Chart(score_summary_df)
        .mark_bar(cornerRadiusEnd=4, height=18)
        .encode(
            y=alt.Y("agent_id:N", title=None, sort="-x", axis=alt.Axis(labelAngle=0, labelLimit=110)),
            x=alt.X(
                "average_hidden_score:Q",
                title=None,
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(values=[0, 25, 50, 75, 100]),
            ),
            color=alt.Color(
                "risk_hint:N",
                title=None,
                scale=alt.Scale(
                    domain=[
                        t(locale, "hidden_score.risk_low"),
                        t(locale, "hidden_score.risk_medium"),
                        t(locale, "hidden_score.risk_high"),
                    ],
                    range=["#16a34a", "#f59e0b", "#dc2626"],
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("agent_id:N", title=t(locale, "column.agent_id")),
                alt.Tooltip("average_hidden_score:Q", title=t(locale, "column.average_hidden_score"), format=".1f"),
                alt.Tooltip("risk_hint:N", title=t(locale, "column.risk_hint")),
            ],
        )
        .properties(height=240)
    )


def customers_to_dataframe(customers, locale: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": c.id,
                "customer": c.name,
                "stage": translated_stage(locale, c.stage.value),
                "agent_id": c.agent_id,
                "phone": c.phone,
                "next_meeting_date": c.next_meeting_date.isoformat() if c.next_meeting_date else "",
                "today_meeting": yes_no(locale, c.next_meeting_date == date.today()),
                "notes": c.notes,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for c in customers
        ],
        columns=[
            "id",
            "customer",
            "stage",
            "agent_id",
            "phone",
            "next_meeting_date",
            "today_meeting",
            "notes",
            "created_at",
        ],
    )


def today_schedule_to_dataframe(customers, locale: str) -> pd.DataFrame:
    sorted_customers = sorted(customers, key=lambda customer: schedule_sort_rank(customer.stage))
    return pd.DataFrame(
        [
            {
                "customer": customer.name,
                "phone": customer.phone,
                "stage": translated_stage(locale, customer.stage.value),
                "agent_id": customer.agent_id,
                "notes": customer.notes,
                "today_meeting": yes_no(locale, customer.next_meeting_date == date.today()),
                "priority": t(locale, schedule_priority_key(customer.stage)),
            }
            for customer in sorted_customers
        ],
        columns=["customer", "phone", "stage", "agent_id", "notes", "today_meeting", "priority"],
    )


def filter_customers(customers, search_text: str = "", stage: str | None = None):
    query = search_text.strip().lower()
    filtered = customers
    if stage:
        filtered = [customer for customer in filtered if customer.stage.value == stage]
    if query:
        filtered = [
            customer
            for customer in filtered
            if query in customer.name.lower()
            or query in customer.phone.lower()
            or query in customer.notes.lower()
            or query in customer.agent_id.lower()
        ]
    return filtered


def daily_logs_to_dataframe(logs) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": l.id,
                "date": l.activity_date.isoformat(),
                "agent_id": l.agent_id,
                "calls": l.call_count,
                "whatsapp": l.whatsapp_count,
                "appointments": l.appointment_count,
                "meetings": l.meeting_count,
                "closings": l.closing_count,
                "notes": l.notes,
                "created_at": l.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for l in logs
        ],
        columns=[
            "id",
            "date",
            "agent_id",
            "calls",
            "whatsapp",
            "appointments",
            "meetings",
            "closings",
            "notes",
            "created_at",
        ],
    )


def visible_followups_to_dataframe(repo: SQLiteGroupTrainingRepository, user, locale: str, pending_only: bool = False) -> pd.DataFrame:
    customers = repo.list_customers(TENANT_ID, agent_id=user.id if user.role == UserRole.AGENT else None)
    customer_map = {customer.id: customer for customer in customers}
    visible_agent_ids = {user.id} if user.role == UserRole.AGENT else {customer.agent_id for customer in customers}
    followups = [
        followup
        for followup in repo.list_followups(TENANT_ID)
        if followup.agent_id in visible_agent_ids and followup.customer_id in customer_map
    ]
    if pending_only:
        followups = [followup for followup in followups if followup.next_action.strip()]
    return pd.DataFrame(
        [
            {
                "customer": customer_map[followup.customer_id].name,
                "agent_id": followup.agent_id,
                "note": followup.note,
                "next_action": followup.next_action,
                "created_at": followup.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for followup in followups
        ],
        columns=["customer", "agent_id", "note", "next_action", "created_at"],
    )


def render_csv_download(label: str, dataframe: pd.DataFrame, file_name: str, key: str, locale: str) -> None:
    export_dataframe = localize_columns(dataframe, locale)
    st.download_button(
        label,
        export_dataframe.to_csv(index=False).encode("utf-8-sig"),
        file_name=file_name,
        mime="text/csv",
        key=key,
        disabled=dataframe.empty,
    )


@st.cache_resource
def get_repo() -> SQLiteGroupTrainingRepository:
    return SQLiteGroupTrainingRepository(os.environ.get("BUILDWAY_GROUP_TRAINING_DB"))


def login_panel(repo: SQLiteGroupTrainingRepository, locale: str):
    if st.session_state.get("gt_user_id"):
        user = repo.get_user(TENANT_ID, st.session_state["gt_user_id"])
        if user:
            with st.sidebar:
                st.caption(t(locale, "auth.signed_in", email=user.email))
                if st.button(t(locale, "auth.logout")):
                    st.session_state.pop("gt_user_id", None)
                    st.rerun()
            return user

    login_tab, signup_tab, reset_tab = st.tabs(
        [t(locale, "auth.login_title"), t(locale, "auth.signup_title"), t(locale, "auth.forgot_password")]
    )
    with login_tab:
        st.subheader(t(locale, "auth.login_title"))
        with st.form("login_form"):
            email = st.text_input(t(locale, "auth.email"))
            password = st.text_input(t(locale, "auth.password"), type="password")
            submit = st.form_submit_button(t(locale, "auth.login_button"))
        if submit:
            user = AuthService(repo).authenticate(TENANT_ID, email, password)
            if user:
                st.session_state["gt_user_id"] = user.id
                st.rerun()
            st.error(t(locale, "auth.invalid_login"))
    with signup_tab:
        st.subheader(t(locale, "auth.signup_title"))
        role_options = {
            t(locale, "role.Agent"): UserRole.AGENT.value,
            t(locale, "role.Manager"): UserRole.MANAGER.value,
        }
        with st.form("signup_form"):
            name = st.text_input(t(locale, "auth.signup_name"))
            signup_email = st.text_input(t(locale, "auth.email"), key="signup_email")
            signup_password = st.text_input(t(locale, "auth.password"), type="password", key="signup_password")
            confirm_password = st.text_input(t(locale, "auth.confirm_password"), type="password")
            selected_role_label = st.selectbox(t(locale, "auth.signup_role"), list(role_options.keys()))
            signup_submit = st.form_submit_button(t(locale, "auth.signup_submit"))
        if signup_submit:
            ok, message_key = signup_user(
                repo,
                name,
                signup_email,
                signup_password,
                confirm_password,
                role_options[selected_role_label],
            )
            if ok:
                st.success(t(locale, message_key))
            else:
                st.error(t(locale, message_key))
    with reset_tab:
        st.subheader(t(locale, "auth.forgot_password"))
        with st.form("password_reset_form"):
            reset_email = st.text_input(t(locale, "auth.email"), key="reset_email")
            reset_submit = st.form_submit_button(t(locale, "auth.reset_submit"))
        if reset_submit:
            st.info(t(locale, request_password_reset(repo, reset_email)))
    return None


def visible_agents(repo: SQLiteGroupTrainingRepository, user):
    if user.role == UserRole.AGENT:
        return [user]
    manager_id = user.id if user.role == UserRole.MANAGER else "mgr_001"
    return repo.list_agents_for_manager(TENANT_ID, manager_id)


def customer_page(user, locale: str) -> None:
    repo = get_repo()
    service = CustomerService(repo)
    st.subheader(t(locale, "customer.title"))

    visible_agent_id = user.id if user.role == UserRole.AGENT else None
    customers = service.repo.list_customers(TENANT_ID, agent_id=visible_agent_id)
    search_col, stage_col, export_col = st.columns([2, 1, 1])
    search_text = search_col.text_input(
        t(locale, "customer.search"),
        placeholder=t(locale, "customer.search_placeholder"),
    )
    stage_options = {t(locale, "customer.stage_all"): None}
    stage_options.update({translated_stage(locale, stage.value): stage.value for stage in CustomerStage})
    selected_stage_label = stage_col.selectbox(t(locale, "customer.stage_filter"), list(stage_options.keys()))
    stage_filter = stage_options[selected_stage_label]
    filtered_customers = filter_customers(customers, search_text, stage_filter)
    customers_df = customers_to_dataframe(filtered_customers, locale)
    export_col.write("")
    export_col.write("")
    render_csv_download(
        t(locale, "customer.export_csv"),
        customers_df,
        "buildway_customers.csv",
        "customers_csv",
        locale,
    )
    with st.expander(t(locale, "customer.import_csv")):
        import_agents = visible_agents(repo, user)
        target_agent_id = user.id
        if user.role != UserRole.AGENT and import_agents:
            agent_options = {f"{agent.name} ({agent.email})": agent.id for agent in import_agents}
            selected_agent_label = st.selectbox(t(locale, "customer.import_agent"), list(agent_options.keys()))
            target_agent_id = agent_options[selected_agent_label]
        uploaded_csv = st.file_uploader(t(locale, "customer.upload_csv"), type=["csv"], key="customer_csv_import")
        if uploaded_csv:
            try:
                csv_dataframe = pd.read_csv(uploaded_csv)
                preview_dataframe = normalize_customer_import_dataframe(csv_dataframe)
                st.session_state["customer_csv_import_preview"] = preview_dataframe
                st.session_state["customer_csv_import_agent_id"] = target_agent_id
                st.markdown(t(locale, "customer.import_preview"))
                st.dataframe(
                    localize_columns(
                        preview_dataframe.assign(next_meeting_date=preview_dataframe["next_meeting_date"].astype(str)),
                        locale,
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                if preview_dataframe.empty:
                    st.warning(t(locale, "customer.import_no_valid_rows"))
            except Exception as exc:
                st.error(t(locale, "customer.import_failed", error=str(exc)))
        preview_dataframe = st.session_state.get("customer_csv_import_preview")
        if preview_dataframe is not None:
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button(t(locale, "customer.confirm_import"), disabled=preview_dataframe.empty):
                imported_count = import_customers_from_dataframe(
                    repo,
                    user,
                    preview_dataframe,
                    st.session_state.get("customer_csv_import_agent_id"),
                )
                st.session_state.pop("customer_csv_import_preview", None)
                st.session_state.pop("customer_csv_import_agent_id", None)
                st.success(t(locale, "customer.import_success", count=imported_count))
                st.rerun()
            if cancel_col.button(t(locale, "customer.cancel_import")):
                st.session_state.pop("customer_csv_import_preview", None)
                st.session_state.pop("customer_csv_import_agent_id", None)
                st.rerun()
    st.caption(t(locale, "customer.showing_count", filtered=len(filtered_customers), total=len(customers)))
    st.dataframe(
        localize_columns(customers_df.drop(columns=["id", "created_at"]), locale),
        use_container_width=True,
        hide_index=True,
    )

    with st.form("customer_form"):
        st.markdown(t(locale, "customer.add"))
        name = st.text_input(t(locale, "customer.name"))
        phone = st.text_input(t(locale, "customer.phone"))
        stage_labels = {translated_stage(locale, stage.value): stage.value for stage in CustomerStage}
        selected_stage = st.selectbox(t(locale, "customer.stage"), list(stage_labels.keys()))
        stage = stage_labels[selected_stage]
        next_meeting = st.date_input(t(locale, "customer.next_meeting_date"), value=date.today())
        notes = st.text_area(t(locale, "customer.notes"))
        agents = visible_agents(repo, user)
        agent_options = {f"{agent.name} ({agent.email})": agent for agent in agents}
        selected_agent_label = None
        if user.role != UserRole.AGENT and agent_options:
            selected_agent_label = st.selectbox(t(locale, "customer.agent"), list(agent_options.keys()))
        submit = st.form_submit_button(t(locale, "customer.save"))
    if submit:
        agent = user if user.role == UserRole.AGENT else agent_options[selected_agent_label]
        service.create_customer(
            TENANT_ID,
            agent.team_id or DEFAULT_TEAM_ID,
            agent.id,
            name,
            stage,
            phone,
            notes,
            next_meeting,
        )
        st.success(t(locale, "customer.saved"))
        st.rerun()

    if customers:
        st.subheader(t(locale, "customer.followup_history"))
        customer_map = {f"{c.name} ({c.id})": c for c in filtered_customers or customers}
        selected_customer = customer_map[st.selectbox(t(locale, "customer.customer"), list(customer_map.keys()))]
        with st.form("followup_form"):
            note = st.text_area(t(locale, "customer.followup_note"))
            next_action = st.text_input(t(locale, "customer.next_action"))
            save_followup = st.form_submit_button(t(locale, "customer.save_followup"))
        if save_followup:
            service.add_followup(TENANT_ID, selected_customer.id, user.id, note, next_action)
            st.success(t(locale, "customer.followup_saved"))
            st.rerun()
        st.dataframe(
            localize_columns(
                pd.DataFrame(
                    [
                        {
                            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
                            "agent_id": f.agent_id,
                            "note": f.note,
                            "next_action": f.next_action,
                        }
                        for f in service.customer_history(TENANT_ID, selected_customer.id)
                    ],
                    columns=["created_at", "agent_id", "note", "next_action"],
                ),
                locale,
            ),
            use_container_width=True,
            hide_index=True,
        )
    recent_followups_df = visible_followups_to_dataframe(repo, user, locale)
    st.subheader(t(locale, "customer.recent_followups"))
    if recent_followups_df.empty:
        st.info(t(locale, "customer.no_recent_followups"))
    else:
        st.dataframe(
            localize_columns(recent_followups_df, locale),
            use_container_width=True,
            hide_index=True,
        )


def daily_log_page(user, locale: str) -> None:
    repo = get_repo()
    service = DailyLogService(repo)
    st.subheader(t(locale, "daily.title"))

    with st.form("daily_log_form"):
        log_date = st.date_input(t(locale, "daily.date"), value=date.today())
        call_count = st.number_input(t(locale, "daily.call_count"), min_value=0, value=10)
        whatsapp_count = st.number_input(t(locale, "daily.whatsapp_count"), min_value=0, value=8)
        appointment_count = st.number_input(t(locale, "daily.appointment_count"), min_value=0, value=1)
        meeting_count = st.number_input(t(locale, "daily.meeting_count"), min_value=0, value=1)
        closing_count = st.number_input(t(locale, "daily.closing_count"), min_value=0, value=0)
        notes = st.text_area(t(locale, "daily.notes"))
        agents = visible_agents(repo, user)
        agent_options = {f"{agent.name} ({agent.email})": agent for agent in agents}
        selected_agent_label = None
        if user.role != UserRole.AGENT and agent_options:
            selected_agent_label = st.selectbox(t(locale, "daily.agent"), list(agent_options.keys()), key="daily_log_agent")
        submit = st.form_submit_button(t(locale, "daily.submit_log"))
    if submit:
        agent = user if user.role == UserRole.AGENT else agent_options[selected_agent_label]
        log = service.create_log(
            TENANT_ID,
            agent.team_id or DEFAULT_TEAM_ID,
            agent.id,
            log_date,
            int(call_count),
            int(whatsapp_count),
            int(appointment_count),
            int(meeting_count),
            int(closing_count),
            notes,
        )
        repo.add_review(review_daily_performance(log))
        repo.add_closing_score(calculate_hidden_closing_score(log))
        st.success(t(locale, "daily.saved"))
        st.rerun()

    logs = repo.list_logs(TENANT_ID, agent_id=user.id if user.role == UserRole.AGENT else None)
    logs_df = daily_logs_to_dataframe(logs)
    render_csv_download(t(locale, "daily.export_csv"), logs_df, "buildway_daily_logs.csv", "daily_logs_csv", locale)
    st.dataframe(
        localize_columns(logs_df.drop(columns=["id", "created_at"]), locale),
        use_container_width=True,
        hide_index=True,
    )


def ocr_data_type_options(locale: str) -> dict[str, str]:
    return {
        t(locale, "ocr.customer"): "customer",
        t(locale, "ocr.daily_log"): "daily_log",
        t(locale, "ocr.follow_up_note"): "follow_up_note",
    }


def ocr_missing_fields(data_type: str, structured: dict) -> list[str]:
    required = {
        "customer": ["name", "stage"],
        "daily_log": ["activity_date"],
        "follow_up_note": ["customer_name", "notes"],
    }.get(data_type, [])
    return [field for field in required if not structured.get(field)]


def render_ocr_customer_form(user, locale: str, structured: dict) -> None:
    repo = get_repo()
    service = CustomerService(repo)
    agents = visible_agents(repo, user)
    agent_options = {f"{agent.name} ({agent.email})": agent for agent in agents}
    stage_labels = {translated_stage(locale, stage.value): stage.value for stage in CustomerStage}
    parsed_stage = structured.get("stage") if structured.get("stage") in [stage.value for stage in CustomerStage] else "Warm"
    default_stage_label = translated_stage(locale, parsed_stage)

    with st.form("ocr_customer_confirm_form"):
        st.markdown(t(locale, "ocr.edit_before_save"))
        name = st.text_input(t(locale, "customer.name"), value=structured.get("name", ""))
        phone = st.text_input(t(locale, "customer.phone"), value=structured.get("phone", ""))
        email = st.text_input(t(locale, "ocr.email"), value=structured.get("email", ""))
        selected_stage = st.selectbox(
            t(locale, "customer.stage"),
            list(stage_labels.keys()),
            index=list(stage_labels.keys()).index(default_stage_label) if default_stage_label in stage_labels else 0,
        )
        source = st.text_input(t(locale, "ocr.source"), value=structured.get("source", ""))
        next_meeting = st.date_input(
            t(locale, "ocr.next_follow_up_date"),
            value=parse_iso_date_or_today(structured.get("next_follow_up_date", "")),
        )
        notes = st.text_area(t(locale, "customer.notes"), value=structured.get("notes", ""))
        next_action = st.text_input(t(locale, "customer.next_action"), value=structured.get("next_action", ""))
        selected_agent_label = None
        if user.role != UserRole.AGENT and agent_options:
            selected_agent_label = st.selectbox(t(locale, "customer.agent"), list(agent_options.keys()), key="ocr_customer_agent")
        confirm = st.form_submit_button(t(locale, "ocr.confirm_save"))
    if confirm:
        agent = user if user.role == UserRole.AGENT else agent_options[selected_agent_label]
        saved_notes = combine_notes(
            notes,
            f"{t(locale, 'ocr.email')}: {email}" if email else "",
            f"{t(locale, 'ocr.source')}: {source}" if source else "",
            f"{t(locale, 'customer.next_action')}: {next_action}" if next_action else "",
        )
        try:
            service.create_customer(TENANT_ID, agent.team_id or DEFAULT_TEAM_ID, agent.id, name, stage_labels[selected_stage], phone, saved_notes, next_meeting)
        except ValueError as exc:
            st.error(t(locale, "ocr.save_failed", error=str(exc)))
            return
        st.session_state.pop("ocr_result", None)
        st.session_state["ocr_flash_success"] = True
        st.rerun()


def render_ocr_daily_log_form(user, locale: str, structured: dict) -> None:
    repo = get_repo()
    service = DailyLogService(repo)
    agents = visible_agents(repo, user)
    agent_options = {f"{agent.name} ({agent.email})": agent for agent in agents}
    with st.form("ocr_daily_log_confirm_form"):
        st.markdown(t(locale, "ocr.edit_before_save"))
        customer_name = st.text_input(t(locale, "ocr.customer_name"), value=structured.get("customer_name", ""))
        activity_type = st.text_input(t(locale, "ocr.activity_type"), value=structured.get("activity_type", ""))
        activity_date = st.date_input(t(locale, "daily.date"), value=parse_iso_date_or_today(structured.get("activity_date", "")))
        call_count = st.number_input(t(locale, "daily.call_count"), min_value=0, value=int(structured.get("call_count") or 0))
        whatsapp_count = st.number_input(t(locale, "daily.whatsapp_count"), min_value=0, value=int(structured.get("whatsapp_count") or 0))
        appointment_count = st.number_input(t(locale, "daily.appointment_count"), min_value=0, value=int(structured.get("appointment_count") or 0))
        meeting_count = st.number_input(t(locale, "daily.meeting_count"), min_value=0, value=int(structured.get("meeting_count") or 0))
        closed_count = st.number_input(t(locale, "daily.closing_count"), min_value=0, value=int(structured.get("closed_count") or 0))
        notes = st.text_area(t(locale, "daily.notes"), value=structured.get("notes", ""))
        selected_agent_label = None
        if user.role != UserRole.AGENT and agent_options:
            selected_agent_label = st.selectbox(t(locale, "daily.agent"), list(agent_options.keys()), key="ocr_daily_agent")
        confirm = st.form_submit_button(t(locale, "ocr.confirm_save"))
    if confirm:
        agent = user if user.role == UserRole.AGENT else agent_options[selected_agent_label]
        saved_notes = combine_notes(
            notes,
            f"{t(locale, 'ocr.customer_name')}: {customer_name}" if customer_name else "",
            f"{t(locale, 'ocr.activity_type')}: {activity_type}" if activity_type else "",
        )
        log = service.create_log(
            TENANT_ID,
            agent.team_id or DEFAULT_TEAM_ID,
            agent.id,
            activity_date,
            int(call_count),
            int(whatsapp_count),
            int(appointment_count),
            int(meeting_count),
            int(closed_count),
            saved_notes,
        )
        repo.add_review(review_daily_performance(log))
        repo.add_closing_score(calculate_hidden_closing_score(log))
        st.session_state.pop("ocr_result", None)
        st.session_state["ocr_flash_success"] = True
        st.rerun()


def render_ocr_follow_up_form(user, locale: str, structured: dict) -> None:
    repo = get_repo()
    service = CustomerService(repo)
    customers = repo.list_customers(TENANT_ID, agent_id=user.id if user.role == UserRole.AGENT else None)
    if not customers:
        st.warning(t(locale, "ocr.follow_up_customer_missing"))
        return
    customer_options = {f"{customer.name} ({customer.id})": customer for customer in customers}
    matched_label = next(
        (label for label, customer in customer_options.items() if customer.name.lower() == structured.get("customer_name", "").strip().lower()),
        next(iter(customer_options)),
    )
    with st.form("ocr_follow_up_confirm_form"):
        st.markdown(t(locale, "ocr.edit_before_save"))
        selected_label = st.selectbox(
            t(locale, "customer.customer"),
            list(customer_options.keys()),
            index=list(customer_options.keys()).index(matched_label),
        )
        note = st.text_area(t(locale, "customer.followup_note"), value=structured.get("notes", ""))
        next_action = st.text_input(t(locale, "customer.next_action"), value=structured.get("next_action", ""))
        follow_up_date = st.date_input(
            t(locale, "ocr.next_follow_up_date"),
            value=parse_iso_date_or_today(structured.get("next_follow_up_date", "")),
        )
        confirm = st.form_submit_button(t(locale, "ocr.confirm_save"))
    if confirm:
        saved_action = combine_notes(next_action, f"{t(locale, 'ocr.next_follow_up_date')}: {follow_up_date.isoformat()}")
        try:
            service.add_followup(TENANT_ID, customer_options[selected_label].id, user.id, note, saved_action)
        except ValueError as exc:
            st.error(t(locale, "ocr.save_failed", error=str(exc)))
            return
        st.session_state.pop("ocr_result", None)
        st.session_state["ocr_flash_success"] = True
        st.rerun()


def ocr_capture_page(user, locale: str) -> None:
    st.subheader(t(locale, "ocr.title"))
    st.caption(t(locale, "ocr.description"))
    if st.session_state.pop("ocr_flash_success", False):
        st.success(t(locale, "ocr.save_success"))
    uploaded_file = st.file_uploader(t(locale, "ocr.upload_image"), type=["png", "jpg", "jpeg", "pdf", "csv", "xlsx"])
    data_type_options = ocr_data_type_options(locale)
    selected_data_type_label = st.selectbox(t(locale, "ocr.data_type"), list(data_type_options.keys()))
    selected_data_type = data_type_options[selected_data_type_label]

    file_bytes = b""
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        st.info(t(locale, "ocr.demo_file_received"))
        file_info_df = pd.DataFrame(
            [
                {
                    "file_name": uploaded_file.name,
                    "file_size": len(file_bytes),
                    "file_type": uploaded_file.type or Path(uploaded_file.name).suffix.lower().lstrip("."),
                }
            ]
        )
        st.dataframe(localize_columns(file_info_df, locale), use_container_width=True, hide_index=True)
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            st.markdown(t(locale, "ocr.preview"))
            st.image(file_bytes, use_container_width=True)
        else:
            st.info(t(locale, "ocr.non_image_received"))

    if st.button(t(locale, "ocr.start_extract"), disabled=not bool(file_bytes)):
        extraction = extract_text_from_image(file_bytes)
        if not os.environ.get("GEMINI_API_KEY"):
            st.info(t(locale, "ocr.no_api_key"))
        if not extraction["ok"]:
            st.error(t(locale, "ocr.extract_failed", error=extraction.get("error") or ""))
            return
        structured = convert_ocr_text_to_structured_data(extraction["raw_text"], selected_data_type)
        st.session_state["ocr_result"] = {
            "data_type": selected_data_type,
            "raw_text": extraction["raw_text"],
            "provider": extraction["provider"],
            "structured": structured,
        }

    result = st.session_state.get("ocr_result")
    if not result:
        return
    st.caption(t(locale, "ocr.provider", provider=result["provider"]))
    st.markdown(t(locale, "ocr.raw_text"))
    st.text_area(t(locale, "ocr.raw_text"), value=result["raw_text"], height=160, disabled=True, label_visibility="collapsed")
    st.markdown(t(locale, "ocr.structured_result"))
    st.json(result["structured"])
    missing = ocr_missing_fields(result["data_type"], result["structured"])
    if missing:
        st.warning(t(locale, "ocr.missing_fields", fields=", ".join(t(locale, f"ocr.field.{field}") for field in missing)))

    if result["data_type"] == "daily_log":
        render_ocr_daily_log_form(user, locale, result["structured"])
    elif result["data_type"] == "follow_up_note":
        render_ocr_follow_up_form(user, locale, result["structured"])
    else:
        render_ocr_customer_form(user, locale, result["structured"])


def today_schedule_page(user, locale: str) -> None:
    repo = get_repo()
    st.subheader(t(locale, "schedule.title"))
    visible_agent_id = user.id if user.role == UserRole.AGENT else None
    customers = [
        customer
        for customer in repo.list_customers(TENANT_ID, agent_id=visible_agent_id)
        if customer.next_meeting_date == date.today()
    ]
    schedule_df = today_schedule_to_dataframe(customers, locale)
    st.caption(t(locale, "schedule.showing_count", total=len(customers)))
    st.dataframe(
        localize_columns(schedule_df, locale),
        use_container_width=True,
        hide_index=True,
    )
    st.info(t(locale, schedule_recommendation_key(customers)))
    pending_followups_df = visible_followups_to_dataframe(repo, user, locale, pending_only=True)
    st.subheader(t(locale, "schedule.pending_followups"))
    if pending_followups_df.empty:
        st.info(t(locale, "schedule.no_pending_followups"))
    else:
        st.dataframe(
            localize_columns(pending_followups_df, locale),
            use_container_width=True,
            hide_index=True,
        )


def ai_training_page(user, locale: str) -> None:
    repo = get_repo()
    st.subheader(t(locale, "training.title"))
    render_scoring_basis(locale)
    reviews = repo.list_reviews(TENANT_ID, agent_id=user.id if user.role == UserRole.AGENT else None)
    logs = repo.list_logs(TENANT_ID, agent_id=user.id if user.role == UserRole.AGENT else None)
    log_index = logs_by_agent_and_date(logs)
    st.dataframe(
        localize_columns(
            pd.DataFrame(
                [
                    {
                        "date": r.review_date,
                        "agent_id": r.agent_id,
                        "summary": localized_review_summary(
                            locale,
                            log_index.get((r.agent_id, r.review_date)),
                            r.summary,
                        ),
                        "advice": localized_review_advice(
                            locale,
                            log_index.get((r.agent_id, r.review_date)),
                            r.risk_level,
                            r.improvement_advice,
                        ),
                        "manager_feedback": ""
                        if user.role == UserRole.AGENT
                        else t(locale, "training.manager_feedback"),
                        "risk": translated_risk(locale, r.risk_level),
                    }
                    for r in reviews
                ],
                columns=["date", "agent_id", "summary", "advice", "manager_feedback", "risk"],
            ),
            locale,
        ),
        use_container_width=True,
        hide_index=True,
    )
    if user.role == UserRole.AGENT:
        st.info(t(locale, "training.hidden_score_agent_info"))


def manager_dashboard_page(user, locale: str) -> None:
    if user.role == UserRole.AGENT:
        st.warning(t(locale, "dashboard.agent_blocked"))
        return
    repo = get_repo()
    manager_id = user.id if user.role == UserRole.MANAGER else "mgr_001"
    dashboard = DashboardService(repo).manager_dashboard(TENANT_ID, manager_id, user.role)
    st.subheader(t(locale, "dashboard.title"))
    render_scoring_basis(locale)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t(locale, "dashboard.team_agents"), len(dashboard["agents"]))
    c2.metric(t(locale, "dashboard.daily_logs"), len(dashboard["daily_logs"]))
    c3.metric(t(locale, "dashboard.ai_reviews"), len(dashboard["reviews"]))
    c4.metric(t(locale, "dashboard.high_risk_members"), len(dashboard["high_risk_agent_ids"]))

    chart_col_1, chart_col_2 = st.columns(2)
    logs_df = daily_logs_to_dataframe(dashboard["daily_logs"])
    if not logs_df.empty:
        chart_col_1.markdown(t(locale, "dashboard.daily_activity_trend"))
        chart_col_1.altair_chart(activity_chart(logs_df, locale), use_container_width=True)
    else:
        chart_col_1.info(t(locale, "dashboard.no_daily_log_data"))

    team_ids = {agent.team_id for agent in dashboard["agents"] if agent.team_id}
    customers = [customer for team_id in team_ids for customer in repo.list_customers(TENANT_ID, team_id=team_id)]
    if customers:
        chart_col_2.markdown(t(locale, "dashboard.customers_by_stage"))
        chart_col_2.altair_chart(stage_chart(customers, locale), use_container_width=True)
    else:
        chart_col_2.info(t(locale, "dashboard.no_customer_data"))

    team_col, score_col = st.columns(2)
    team_col.markdown(t(locale, "dashboard.team_downline"))
    team_col.dataframe(
        localize_columns(
            pd.DataFrame(
                [{"agent_id": a.id, "name": a.name, "email": a.email, "team_id": a.team_id} for a in dashboard["agents"]],
                columns=["agent_id", "name", "email", "team_id"],
            ),
            locale,
        ),
        use_container_width=True,
        hide_index=True,
    )
    score_col.markdown(t(locale, "dashboard.hidden_closing_score"))
    scores_df = pd.DataFrame(
        [
            {
                "date": s.score_date.isoformat(),
                "agent_id": s.agent_id,
                "hidden_score": s.hidden_score,
                "rationale": t(locale, "hidden_score.rationale"),
            }
            for s in dashboard["closing_scores"]
        ],
        columns=["date", "agent_id", "hidden_score", "rationale"],
    )
    score_summary_df = hidden_score_summary(scores_df, locale)
    if not scores_df.empty:
        average_score = score_summary_df["average_hidden_score"].mean()
        score_col.metric(t(locale, "hidden_score.average_by_agent"), f"{average_score:.1f}")
        score_col.altair_chart(hidden_score_chart(score_summary_df, locale), use_container_width=True)
        score_col.dataframe(
            localize_columns(score_summary_df, locale),
            use_container_width=True,
            hide_index=True,
        )
    score_col.dataframe(
        localize_columns(scores_df, locale),
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    locale = st.session_state.get("gt_locale", DEFAULT_LOCALE)
    st.set_page_config(page_title=t(locale, "app.page_title"), layout="wide")
    repo = get_repo()
    st.title(t(locale, "app.title"))
    if developer_mode_enabled():
        st.caption(t(locale, "app.caption"))
    with st.sidebar:
        selected_locale = st.selectbox(
            t(locale, "language.label"),
            list(SUPPORTED_LOCALES.keys()),
            format_func=lambda option: SUPPORTED_LOCALES[option],
            key="gt_locale",
        )
    locale = selected_locale

    user = login_panel(repo, locale)
    if user is None:
        if developer_mode_enabled():
            st.caption(t(locale, "system.sqlite_database", path=default_sqlite_path()))
        return

    st.sidebar.caption(t(locale, "sidebar.tenant_id", tenant_id=TENANT_ID))
    st.sidebar.caption(t(locale, "sidebar.user_id", user_id=user.id))
    st.sidebar.caption(t(locale, "sidebar.role", role=translated_role(locale, user.role)))

    pages = {
        t(locale, "nav.customer_crm"): customer_page,
        t(locale, "nav.daily_activity_log"): daily_log_page,
        t(locale, "nav.today_schedule"): today_schedule_page,
        t(locale, "nav.ocr_data_capture"): ocr_capture_page,
        t(locale, "nav.ai_training_agent"): ai_training_page,
    }
    if user.role != UserRole.AGENT:
        pages[t(locale, "nav.manager_dashboard")] = manager_dashboard_page
    selected_page = st.sidebar.radio(t(locale, "nav.label"), list(pages.keys()))
    pages[selected_page](user, locale)


if __name__ == "__main__":
    main()
