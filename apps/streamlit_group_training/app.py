"""
Buildway AI Core - Group Training MVP.

Run with:
    streamlit run apps/streamlit_group_training/app.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
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
from apps.streamlit_group_training.services.demo_dataset_service import (
    demo_dataset_allowed,
    generate_demo_ai_insights,
    generate_demo_dashboard_metrics,
    seed_demo_dataset,
)
from verticals.group_training.agents.closing_agent import calculate_hidden_closing_score
from verticals.group_training.agents.closing_agent import hidden_score_risk_level
from verticals.group_training.agents.coaching_agent import build_coaching_plan
from verticals.group_training.agents.customer_opportunity_agent import (
    analyze_customer_opportunity,
    rank_customer_opportunities,
)
from verticals.group_training.agents.manager_insight_agent import build_manager_insight
from verticals.group_training.agents.sales_performance_agent import analyze_sales_performance
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
RAW_I18N_PREFIXES = (
    "nav.",
    "schedule.",
    "training.",
    "dashboard.",
    "risk.",
    "scoring_basis.",
    "scoring.",
    "ocr.",
    "demo.",
    "opportunity.",
    "sales.",
    "coaching.",
    "manager_insight.",
)


def t(locale: str, key: str, **kwargs) -> str:
    return translate(locale, key, **kwargs)


def safe_dict(value):
    """Return value if dict, else empty dict."""
    return value if isinstance(value, dict) else {}


def safe_list(value):
    """Return value if list, else empty list."""
    return value if isinstance(value, list) else []


def safe_text(value, fallback=""):
    """Return value if non-empty string, else fallback."""
    return value if isinstance(value, str) and value.strip() else fallback


def safe_number(value, default=0):
    """Return numeric value, else default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def agent_display_name(repo: SQLiteGroupTrainingRepository, agent_id: str) -> str:
    user = repo.get_user(TENANT_ID, agent_id)
    if not user:
        return agent_id
    if user.name and user.email:
        return f"{user.name} ({user.email})"
    return user.name or user.email or agent_id


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


def render_simple_table(dataframe: pd.DataFrame, locale: str, container=st) -> None:
    localized = localize_columns(dataframe, locale)
    if localized.empty:
        container.table(localized)
        return
    html = localized.to_html(index=False, escape=True, classes="simple-demo-table")
    container.markdown(
        f"""
        <div style="overflow-x:auto; width:100%;">
            <style>
            .simple-demo-table {{
                border-collapse: collapse;
                width: 100%;
                min-width: 640px;
                font-size: 0.92rem;
            }}
            .simple-demo-table th,
            .simple-demo-table td {{
                border: 1px solid #e5e7eb;
                padding: 0.5rem 0.65rem;
                text-align: left;
                vertical-align: top;
                white-space: normal;
                word-break: break-word;
            }}
            .simple-demo-table th {{
                background: #f8fafc;
                font-weight: 600;
            }}
            </style>
            {html}
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def customer_followup_recommendation_key(stage: CustomerStage) -> str:
    if stage == CustomerStage.HOT:
        return "followup.recommendation_hot"
    if stage == CustomerStage.PROPOSAL:
        return "followup.recommendation_proposal"
    if stage == CustomerStage.WARM:
        return "followup.recommendation_warm"
    if stage == CustomerStage.COLD:
        return "followup.recommendation_cold"
    if stage == CustomerStage.CLOSED:
        return "followup.recommendation_closed"
    return "followup.recommendation_lost"


def customer_followup_recommendation(customer, locale: str) -> str:
    return t(locale, customer_followup_recommendation_key(customer.stage))


def date_range_start(range_key: str, today: date | None = None) -> date | None:
    today = today or date.today()
    if range_key == "today":
        return today
    if range_key == "last_7_days":
        return today - timedelta(days=6)
    if range_key == "last_30_days":
        return today - timedelta(days=29)
    return None


def filter_by_date_range(rows, attr_name: str, range_key: str, today: date | None = None):
    start = date_range_start(range_key, today)
    if not start:
        return list(rows)
    today = today or date.today()
    return [row for row in rows if start <= getattr(row, attr_name) <= today]


def hidden_score_band(score: int | float) -> str:
    return hidden_score_risk_level(score).lower()


def hidden_score_risk_key(score: float) -> str:
    risk_level = hidden_score_risk_level(score)
    if risk_level == "Low":
        return "low"
    if risk_level == "Medium":
        return "medium"
    if risk_level == "High":
        return "high"
    return "critical"


def hidden_score_risk_i18n_key(score: float) -> str:
    return f"hidden_score.risk_{hidden_score_risk_key(score)}"


def opportunity_priority_key(priority: str) -> str:
    return f"opportunity.priority.{priority.lower()}"


def customer_priority_band(customer) -> str:
    priority_key = schedule_priority_key(customer.stage)
    if priority_key == "schedule.priority_high":
        return "high"
    if priority_key == "schedule.priority_medium":
        return "medium"
    return "low"


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


def hidden_score_summary(scores_df: pd.DataFrame, locale: str) -> pd.DataFrame:
    if scores_df.empty:
        return pd.DataFrame(columns=["agent_id", "average_hidden_score", "risk_hint"])
    summary_df = scores_df.groupby("agent_id", as_index=False)["hidden_score"].mean()
    summary_df["average_hidden_score"] = summary_df["hidden_score"].round(1)
    summary_df["risk_hint"] = summary_df["average_hidden_score"].apply(lambda score: t(locale, hidden_score_risk_i18n_key(score)))
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
                        t(locale, "hidden_score.risk_critical"),
                    ],
                    range=["#16a34a", "#f59e0b", "#dc2626", "#7f1d1d"],
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


def build_customer_opportunity_map(repo: SQLiteGroupTrainingRepository, customers) -> dict[str, object]:
    all_followups = repo.list_followups(TENANT_ID)
    all_logs = repo.list_logs(TENANT_ID)
    return {
        customer.id: analyze_customer_opportunity(
            customer,
            [followup for followup in all_followups if followup.customer_id == customer.id],
            [log for log in all_logs if log.agent_id == customer.agent_id],
        )
        for customer in customers
    }


def customers_to_dataframe(
    customers,
    locale: str,
    repo: SQLiteGroupTrainingRepository | None = None,
    opportunity_map: dict[str, object] | None = None,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": c.id,
                "customer": c.name,
                "stage": translated_stage(locale, c.stage.value),
                "agent_id": agent_display_name(repo, c.agent_id) if repo else c.agent_id,
                "phone": c.phone,
                "next_meeting_date": c.next_meeting_date.isoformat() if c.next_meeting_date else "",
                "today_meeting": yes_no(locale, c.next_meeting_date == date.today()),
                "opportunity_score": opportunity_map[c.id].opportunity_score if opportunity_map and c.id in opportunity_map else "",
                "priority": t(locale, opportunity_priority_key(opportunity_map[c.id].priority)) if opportunity_map and c.id in opportunity_map else t(locale, schedule_priority_key(c.stage)),
                "opportunity_reason": t(locale, opportunity_map[c.id].reason_key) if opportunity_map and c.id in opportunity_map else "",
                "next_best_action": t(locale, opportunity_map[c.id].next_best_action_key) if opportunity_map and c.id in opportunity_map else customer_followup_recommendation(c, locale),
                "suggested_message": t(locale, opportunity_map[c.id].suggested_message_key) if opportunity_map and c.id in opportunity_map else "",
                "followup_deadline": opportunity_map[c.id].followup_deadline.isoformat() if opportunity_map and c.id in opportunity_map else "",
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
            "opportunity_score",
            "priority",
            "opportunity_reason",
            "next_best_action",
            "suggested_message",
            "followup_deadline",
            "notes",
            "created_at",
        ],
    )


def today_schedule_to_dataframe(
    customers,
    locale: str,
    repo: SQLiteGroupTrainingRepository | None = None,
    opportunity_map: dict[str, object] | None = None,
) -> pd.DataFrame:
    if opportunity_map:
        ordered_ids = [analysis.customer_id for analysis in rank_customer_opportunities([opportunity_map[customer.id] for customer in customers])]
        sorted_customers = sorted(customers, key=lambda customer: ordered_ids.index(customer.id))
    else:
        sorted_customers = sorted(customers, key=lambda customer: schedule_sort_rank(customer.stage))
    return pd.DataFrame(
        [
            {
                "customer": customer.name,
                "phone": customer.phone,
                "stage": translated_stage(locale, customer.stage.value),
                "agent_id": agent_display_name(repo, customer.agent_id) if repo else customer.agent_id,
                "notes": customer.notes,
                "today_meeting": yes_no(locale, customer.next_meeting_date == date.today()),
                "opportunity_score": opportunity_map[customer.id].opportunity_score if opportunity_map and customer.id in opportunity_map else "",
                "priority": t(locale, opportunity_priority_key(opportunity_map[customer.id].priority)) if opportunity_map and customer.id in opportunity_map else t(locale, schedule_priority_key(customer.stage)),
                "opportunity_reason": t(locale, opportunity_map[customer.id].reason_key) if opportunity_map and customer.id in opportunity_map else "",
                "contact_method": t(locale, opportunity_map[customer.id].contact_method_key) if opportunity_map and customer.id in opportunity_map else "",
                "next_best_action": t(locale, opportunity_map[customer.id].next_best_action_key) if opportunity_map and customer.id in opportunity_map else "",
                "suggested_message": t(locale, opportunity_map[customer.id].suggested_message_key) if opportunity_map and customer.id in opportunity_map else "",
            }
            for customer in sorted_customers
        ],
        columns=[
            "customer",
            "phone",
            "stage",
            "agent_id",
            "today_meeting",
            "opportunity_score",
            "priority",
            "opportunity_reason",
            "contact_method",
            "next_best_action",
            "suggested_message",
            "notes",
        ],
    )


def filter_customers(
    customers,
    search_text: str = "",
    stage: str | None = None,
    agent_id: str | None = None,
    today_followup: str = "all",
    priority: str = "all",
):
    query = search_text.strip().lower()
    filtered = customers
    if stage:
        filtered = [customer for customer in filtered if customer.stage.value == stage]
    if agent_id:
        filtered = [customer for customer in filtered if customer.agent_id == agent_id]
    if today_followup == "today":
        filtered = [customer for customer in filtered if customer.next_meeting_date == date.today()]
    elif today_followup == "not_today":
        filtered = [customer for customer in filtered if customer.next_meeting_date != date.today()]
    if priority != "all":
        filtered = [customer for customer in filtered if customer_priority_band(customer) == priority]
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


def filter_daily_logs(logs, agent_id: str | None = None, date_range: str = "all", activity_issue: str = "all"):
    filtered = list(logs)
    if agent_id:
        filtered = [log for log in filtered if log.agent_id == agent_id]
    filtered = filter_by_date_range(filtered, "activity_date", date_range)
    if activity_issue == "low_activity":
        filtered = [log for log in filtered if log.call_count + log.whatsapp_count < 10]
    elif activity_issue == "low_closing":
        filtered = [log for log in filtered if log.appointment_count >= 2 and log.closing_count == 0]
    return filtered


def filter_reviews(reviews, agent_id: str | None = None, risk_level: str = "all", date_range: str = "all"):
    filtered = list(reviews)
    if agent_id:
        filtered = [review for review in filtered if review.agent_id == agent_id]
    if risk_level != "all":
        filtered = [review for review in filtered if review.risk_level == risk_level]
    return filter_by_date_range(filtered, "review_date", date_range)


def filter_scores(scores, agent_id: str | None = None, risk_band: str = "all"):
    filtered = list(scores)
    if agent_id:
        filtered = [score for score in filtered if score.agent_id == agent_id]
    if risk_band != "all":
        filtered = [score for score in filtered if hidden_score_band(score.hidden_score) == risk_band]
    return filtered


def build_agent_coaching_plan(logs, reviews, scores, team_logs=None) -> dict:
    latest_score = max(scores, key=lambda score: (score.score_date, score.created_at), default=None)
    latest_review = max(reviews, key=lambda review: (review.review_date, review.created_at), default=None)
    performance = analyze_sales_performance(logs, team_logs=team_logs or logs)
    coaching_plan = build_coaching_plan(performance, latest_score.hidden_score if latest_score else None)

    return {
        "issue": performance.conversion_problem_stage,
        "metrics": {
            **performance.metrics,
            "performance_score": performance.performance_score,
            "latest_hidden_score": latest_score.hidden_score if latest_score else 0,
            "latest_risk": latest_review.risk_level if latest_review else "Low",
        },
        "issue_key": coaching_plan.coaching_topic_key,
        "root_cause_key": coaching_plan.reason_key,
        "training_focus_key": coaching_plan.training_focus_key,
        "next_action_key": coaching_plan.next_action_key,
        "manager_note_key": coaching_plan.manager_action_key,
        "target_metric_key": coaching_plan.target_metric_key,
        "target_deadline": coaching_plan.target_deadline,
        "why_this_coaching_key": coaching_plan.why_this_coaching_key,
        "target_metric": coaching_plan.target_metric,
        "target_date": coaching_plan.target_date,
        "expected_improvement_key": coaching_plan.expected_improvement_key,
        "performance": performance,
        "coaching": coaching_plan,
    }


def coaching_plan_to_dataframe(agent_plans: list[dict], locale: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "agent_id": plan["agent_label"],
                "coaching_issue": t(locale, plan["issue_key"]),
                "root_cause": t(locale, plan["root_cause_key"]),
                "training_focus": t(locale, plan["training_focus_key"]),
                "next_action": t(locale, plan["next_action_key"]),
                "why_this_coaching": t(locale, plan["why_this_coaching_key"]),
                "manager_note": t(locale, plan["manager_note_key"]),
                "target_metric": t(locale, plan["target_metric_key"]),
                "target_date": plan["target_date"].isoformat(),
                "expected_improvement": t(locale, plan["expected_improvement_key"]),
                "performance_score": plan["metrics"]["performance_score"],
                "hidden_score": plan["metrics"]["latest_hidden_score"],
                "risk": translated_risk(locale, plan["metrics"]["latest_risk"]),
            }
            for plan in agent_plans
        ],
        columns=[
            "agent_id",
            "coaching_issue",
            "root_cause",
            "training_focus",
            "next_action",
            "why_this_coaching",
            "manager_note",
            "target_metric",
            "target_date",
            "expected_improvement",
            "performance_score",
            "hidden_score",
            "risk",
        ],
    )


def sales_performance_to_dataframe(agent_plans: list[dict], locale: str) -> pd.DataFrame:
    rows = []
    for plan in agent_plans:
        performance = plan["performance"]
        rows.append(
            {
                "agent_id": plan["agent_label"],
                "performance_score": performance.performance_score,
                "strength": t(locale, performance.strength_key),
                "weakness": t(locale, performance.weakness_key),
                "conversion_problem_stage": t(locale, f"sales.stage.{performance.conversion_problem_stage}"),
                "explanation": t(locale, performance.explanation_key),
                "appointment_rate": f"{performance.metrics['appointment_rate']:.1f}%",
                "meeting_rate": f"{performance.metrics['meeting_rate']:.1f}%",
                "closing_rate": f"{performance.metrics['closing_rate']:.1f}%",
                "team_average": (
                    f"{performance.team_average_comparison['appointment_rate']:.1f}% / "
                    f"{performance.team_average_comparison['meeting_rate']:.1f}% / "
                    f"{performance.team_average_comparison['closing_rate']:.1f}%"
                ),
                "performance_gap": (
                    f"{performance.performance_gap['appointment_rate']:+.1f}% / "
                    f"{performance.performance_gap['meeting_rate']:+.1f}% / "
                    f"{performance.performance_gap['closing_rate']:+.1f}%"
                ),
                "trend_analysis": t(locale, f"sales.trend.{performance.trend_analysis['direction']}"),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "agent_id",
            "performance_score",
            "strength",
            "weakness",
            "conversion_problem_stage",
            "explanation",
            "appointment_rate",
            "meeting_rate",
            "closing_rate",
            "team_average",
            "performance_gap",
            "trend_analysis",
        ],
    )


def customer_opportunities_to_dataframe(customers, opportunity_map: dict[str, object], locale: str, repo=None) -> pd.DataFrame:
    customer_lookup = {customer.id: customer for customer in customers}
    rows = []
    for analysis in rank_customer_opportunities(list(opportunity_map.values())):
        customer = customer_lookup.get(analysis.customer_id)
        if not customer:
            continue
        rows.append(
            {
                "customer": customer.name,
                "agent_id": agent_display_name(repo, customer.agent_id) if repo else customer.agent_id,
                "stage": translated_stage(locale, customer.stage.value),
                "opportunity_score": analysis.opportunity_score,
                "priority": t(locale, opportunity_priority_key(analysis.priority)),
                "opportunity_reason": t(locale, analysis.reason_key),
                "next_best_action": t(locale, analysis.next_best_action_key),
                "followup_deadline": analysis.followup_deadline.isoformat(),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "customer",
            "agent_id",
            "stage",
            "opportunity_score",
            "priority",
            "opportunity_reason",
            "next_best_action",
            "followup_deadline",
        ],
    )


def render_manager_insight_section(
    repo: SQLiteGroupTrainingRepository,
    locale: str,
    agents,
    customers,
    logs,
    scores,
    plans: list[dict],
    opportunity_map: dict[str, object],
) -> None:
    performances = [plan["performance"] for plan in plans]
    insight = build_manager_insight(agents, customers, list(opportunity_map.values()), performances, scores)
    st.subheader(t(locale, "manager_insight.title"))
    st.info(
        t(
            locale,
            insight.summary_key,
            affected_agents=insight.affected_agent_count,
            total_agents=len(agents),
            problem=t(locale, insight.team_problem_key),
        )
    )
    insight_cols = st.columns(2)
    insight_cols[0].markdown(t(locale, "manager_insight.main_problem"))
    insight_cols[0].write(t(locale, insight.team_problem_key))
    insight_cols[0].markdown(t(locale, "manager_insight.ai_recommendation"))
    insight_cols[0].write(t(locale, insight.manager_recommendation_key))
    insight_cols[1].markdown(t(locale, "manager_insight.team_next_action"))
    insight_cols[1].write(t(locale, insight.team_next_action_key))
    insight_cols[1].markdown(t(locale, "manager_insight.high_risk_agents"))
    render_simple_table(risk_agents_to_dataframe(repo, insight.high_risk_agents, locale), locale, insight_cols[1])

    st.markdown(t(locale, "manager_insight.top_customers"))
    top_customer_ids = {analysis.customer_id for analysis in insight.top_customers}
    top_customer_map = {customer_id: opportunity_map[customer_id] for customer_id in top_customer_ids if customer_id in opportunity_map}
    render_simple_table(customer_opportunities_to_dataframe(customers, top_customer_map, locale, repo).head(10), locale)
    with st.expander(t(locale, "explain.basis_title")):
        st.markdown(t(locale, "manager_insight.reason_label"))
        st.write(t(locale, insight.insight_reason_key))
        st.markdown(t(locale, "explain.supporting_metrics"))
        render_simple_table(
            pd.DataFrame(
                [
                    {"metric": t(locale, f"manager_insight.metric.{key}"), "value": value}
                    for key, value in insight.supporting_metrics.items()
                ]
            ),
            locale,
        )
        st.markdown(t(locale, "explain.ai_confidence"))
        st.write(f"{insight.ai_confidence}%")


def render_opportunity_basis(opportunity_map: dict[str, object], locale: str) -> None:
    if not opportunity_map:
        return
    with st.expander(t(locale, "explain.basis_title")):
        rows = []
        for analysis in rank_customer_opportunities(list(opportunity_map.values()))[:10]:
            breakdown = safe_dict(analysis.score_breakdown)
            breakdown_text = ", ".join(
                f"{t(locale, f'opportunity.breakdown.{key}')}={value}"
                for key, value in breakdown.items()
            ) if breakdown else "—"
            
            score_reason = safe_text(analysis.score_reason_key)
            confidence = safe_number(analysis.confidence, 0)
            
            rows.append(
                {
                    "id": analysis.customer_id,
                    "opportunity_score": analysis.opportunity_score,
                    "score_breakdown": breakdown_text,
                    "score_reason": t(locale, score_reason) if score_reason else "—",
                    "confidence": f"{confidence}%",
                }
            )
        if rows:
            render_simple_table(pd.DataFrame(rows), locale)
        else:
            st.info(t(locale, "customer360.no_basis_data"))


def hidden_score_breakdown_dataframe(scores, logs, locale: str) -> pd.DataFrame:
    from verticals.group_training.agents.closing_agent import hidden_score_breakdown

    log_index = {(log.agent_id, log.activity_date): log for log in logs}
    rows = []
    for score in scores:
        log = log_index.get((score.agent_id, score.score_date))
        if not log:
            continue
        breakdown = hidden_score_breakdown(log)
        rows.append(
            {
                "agent_id": score.agent_id,
                "date": score.score_date.isoformat(),
                "activity_score": breakdown["activity_score"],
                "appointment_score": breakdown["appointment_score"],
                "meeting_score": breakdown["meeting_score"],
                "closing_score": breakdown["closing_score"],
                "discipline_score": breakdown["discipline_score"],
                "hidden_score": score.hidden_score,
                "risk": t(locale, hidden_score_risk_i18n_key(score.hidden_score)),
            }
        )
    return pd.DataFrame(rows)


def build_visible_agent_coaching_plans(repo: SQLiteGroupTrainingRepository, agents, logs, reviews, scores) -> list[dict]:
    plans = []
    for agent in agents:
        plan = build_agent_coaching_plan(
            [log for log in logs if log.agent_id == agent.id],
            [review for review in reviews if review.agent_id == agent.id],
            [score for score in scores if score.agent_id == agent.id],
            logs,
        )
        plan["agent_id"] = agent.id
        plan["agent_label"] = agent_display_name(repo, agent.id)
        plans.append(plan)
    return plans


def render_customer_stage_guidance(locale: str) -> None:
    with st.expander(t(locale, "customer.stage_guidance_title")):
        for stage in CustomerStage:
            st.markdown(f"**{translated_stage(locale, stage.value)}**")
            st.caption(t(locale, f"stage_guidance.{stage.value}"))


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
                "agent_id": agent_display_name(repo, followup.agent_id),
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


def render_demo_dataset_controls(repo: SQLiteGroupTrainingRepository, user, locale: str) -> bool:
    if user.role == UserRole.AGENT:
        return False
    user_key = getattr(user, "id", "guest")
    flash = st.session_state.pop("demo_dataset_flash", None)
    if flash:
        st.success(
            t(
                locale,
                flash["message_key"],
                agents=flash["counts"]["agents"],
                customers=flash["counts"]["customers"],
                logs=flash["counts"]["daily_logs"],
            )
        )
    with st.expander(t(locale, "demo.dataset_title")):
        st.caption(t(locale, "demo.dataset_description"))
        if not demo_dataset_allowed(TENANT_ID):
            st.warning(t(locale, "demo.not_allowed"))
            return False
        confirmed = st.checkbox(t(locale, "demo.confirm_reset"), key=f"dashboard_demo_confirm_{user_key}")
        load_col, reset_col = st.columns(2)
        load_clicked = load_col.button(t(locale, "demo.load_dataset"), disabled=not confirmed, key=f"dashboard_demo_load_{user_key}")
        reset_clicked = reset_col.button(t(locale, "demo.reset_dataset"), disabled=not confirmed, key=f"dashboard_demo_reset_{user_key}")
        if load_clicked:
            counts = seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
            st.session_state["demo_dataset_flash"] = {"message_key": "demo.seed_success", "counts": counts}
            st.rerun()
        if reset_clicked:
            counts = seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
            st.session_state["demo_dataset_flash"] = {"message_key": "demo.reset_success", "counts": counts}
            st.rerun()
    return False


def dashboard_metric_rows(metrics: dict) -> list[tuple[str, str]]:
    return [
        ("dashboard.team_total_customers", str(metrics["team_total_customers"])),
        ("dashboard.today_activity_count", str(metrics["today_activity_count"])),
        ("dashboard.weekly_followup_count", str(metrics["weekly_followup_count"])),
        ("dashboard.overdue_followup_count", str(metrics["overdue_followup_count"])),
        ("dashboard.high_potential_customer_count", str(metrics["high_potential_customer_count"])),
        ("dashboard.low_active_agent_count", str(metrics["low_active_agent_count"])),
        ("dashboard.hidden_score_summary", f"{metrics['hidden_score_average']:.1f}"),
        ("dashboard.risk_agents", str(len(metrics["risk_agent_ids"]))),
    ]


def top_agents_to_dataframe(repo: SQLiteGroupTrainingRepository, rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "agent_id": agent_display_name(repo, row["agent_id"]),
                "activity_score": row["activity_score"],
                "hidden_score": row["hidden_score"],
            }
            for row in rows
        ],
        columns=["agent_id", "activity_score", "hidden_score"],
    )


def risk_agents_to_dataframe(repo: SQLiteGroupTrainingRepository, agent_ids: list[str], locale: str) -> pd.DataFrame:
    return pd.DataFrame(
        [{"agent_id": agent_display_name(repo, agent_id), "risk_hint": t(locale, "risk.High")} for agent_id in agent_ids],
        columns=["agent_id", "risk_hint"],
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
                if st.button(t(locale, "auth.logout"), key=f"sidebar_logout_{user.id}"):
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
            selected_role_label = st.selectbox(t(locale, "auth.signup_role"), list(role_options.keys()), key="signup_role_select")
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


def report_agents(repo: SQLiteGroupTrainingRepository, user):
    if user.role == UserRole.AGENT:
        return [user]
    direct_agents = visible_agents(repo, user)
    if direct_agents:
        return direct_agents
    return [candidate for candidate in repo.list_users(TENANT_ID) if candidate.role == UserRole.AGENT]


def render_customer_360(repo, customers, locale: str, user) -> None:
    """Customer 360 detail view with tabs."""
    if not customers:
        return
    st.subheader(t(locale, "customer360.title"))
    customer_map = {f"{c.name} ({c.id[-6:] if len(c.id) > 6 else c.id})": c for c in customers}
    selected_label = st.selectbox(
        t(locale, "customer360.select_customer"),
        list(customer_map.keys()),
        key=f"customer360_select_{user.id}",
    )
    selected = customer_map[selected_label]
    service = CustomerService(repo)
    opportunity_map = build_customer_opportunity_map(repo, [selected])
    opp = opportunity_map.get(selected.id)

    tab_basic, tab_history, tab_ai, tab_basis = st.tabs([
        t(locale, "customer360.tab_basic"),
        t(locale, "customer360.tab_history"),
        t(locale, "customer360.tab_ai"),
        t(locale, "customer360.tab_basis"),
    ])

    with tab_basic:
        col1, col2 = st.columns(2)
        col1.markdown(f"**{t(locale, 'customer.name')}:** {selected.name}")
        col1.markdown(f"**{t(locale, 'customer.phone')}:** {selected.phone or '—'}")
        col1.markdown(f"**{t(locale, 'customer.stage')}:** {translated_stage(locale, selected.stage.value)}")
        col2.markdown(f"**{t(locale, 'customer.agent')}:** {agent_display_name(repo, selected.agent_id)}")
        col2.markdown(f"**{t(locale, 'customer.next_meeting_date')}:** {selected.next_meeting_date.isoformat() if selected.next_meeting_date else '—'}")
        col2.markdown(f"**{t(locale, 'customer.notes')}:** {selected.notes or '—'}")

    with tab_history:
        followups = service.customer_history(TENANT_ID, selected.id)
        if not followups:
            st.info(t(locale, "customer360.no_history"))
        else:
            for f in followups:
                st.markdown(f"**{f.created_at.strftime('%Y-%m-%d %H:%M')}** — {agent_display_name(repo, f.agent_id)}")
                st.write(f.note or "—")
                if f.next_action:
                    st.caption(f"{t(locale, 'customer.next_action')}: {f.next_action}")
                st.divider()

    with tab_ai:
        if opp:
            c1, c2 = st.columns(2)
            c1.metric(t(locale, "customer360.ai_score"), opp.opportunity_score)
            c2.metric(t(locale, "customer360.ai_priority"), t(locale, opportunity_priority_key(opp.priority)))
            st.markdown(f"**{t(locale, 'customer360.reason')}:** {t(locale, opp.reason_key)}")
            st.markdown(f"**{t(locale, 'customer360.next_action')}:** {t(locale, opp.next_best_action_key)}")
            st.markdown(f"**{t(locale, 'customer360.suggested_message')}:** {t(locale, opp.suggested_message_key)}")
            st.markdown(f"**{t(locale, 'customer360.deadline')}:** {opp.followup_deadline.isoformat() if opp.followup_deadline else '—'}")
        else:
            st.info(t(locale, "customer360.no_ai_data"))

    with tab_basis:
        if opp:
            breakdown = opp.score_breakdown if isinstance(opp.score_breakdown, dict) else {}
            if breakdown:
                st.markdown(f"**{t(locale, 'customer360.score_breakdown')}**")
                for key, val in breakdown.items():
                    st.caption(f"{t(locale, f'opportunity.breakdown.{key}')}: {val}")
            score_reason = opp.score_reason_key if isinstance(opp.score_reason_key, str) else ""
            if score_reason:
                st.markdown(f"**{t(locale, 'customer360.score_reason')}:** {t(locale, score_reason)}")
            confidence = opp.confidence if isinstance(opp.confidence, (int, float)) else 0
            st.markdown(f"**{t(locale, 'customer360.confidence')}:** {confidence}%")
        else:
            st.info(t(locale, "customer360.no_basis_data"))


def customer_page(user, locale: str) -> None:
    repo = get_repo()
    service = CustomerService(repo)
    st.subheader(t(locale, "customer.title"))

    visible_agent_id = user.id if user.role == UserRole.AGENT else None
    customers = service.repo.list_customers(TENANT_ID, agent_id=visible_agent_id)
    render_customer_stage_guidance(locale)
    search_col, stage_col, agent_col, today_col, priority_col = st.columns([2, 1, 1, 1, 1])
    search_text = search_col.text_input(
        t(locale, "customer.search"),
        placeholder=t(locale, "customer.search_placeholder"),
    )
    stage_options = {t(locale, "customer.stage_all"): None}
    stage_options.update({translated_stage(locale, stage.value): stage.value for stage in CustomerStage})
    selected_stage_label = stage_col.selectbox(t(locale, "customer.stage_filter"), list(stage_options.keys()), key=f"customer_stage_filter_{user.id}")
    stage_filter = stage_options[selected_stage_label]
    customer_agents = visible_agents(repo, user)
    agent_filter_options = {t(locale, "filter.all"): None}
    agent_filter_options.update({agent_display_name(repo, agent.id): agent.id for agent in customer_agents})
    selected_agent_filter = agent_col.selectbox(t(locale, "filter.agent"), list(agent_filter_options.keys()), key=f"customer_agent_filter_{user.id}")
    today_options = {
        t(locale, "filter.all"): "all",
        t(locale, "filter.today"): "today",
        t(locale, "filter.not_today"): "not_today",
    }
    selected_today_filter = today_col.selectbox(t(locale, "filter.today_followup"), list(today_options.keys()), key=f"customer_today_filter_{user.id}")
    priority_options = {
        t(locale, "filter.all"): "all",
        t(locale, "schedule.priority_high"): "high",
        t(locale, "schedule.priority_medium"): "medium",
        t(locale, "schedule.priority_low"): "low",
    }
    selected_priority_filter = priority_col.selectbox(t(locale, "filter.ai_priority"), list(priority_options.keys()), key=f"customer_priority_filter_{user.id}")
    filtered_customers = filter_customers(
        customers,
        search_text,
        stage_filter,
        agent_filter_options[selected_agent_filter],
        today_options[selected_today_filter],
        priority_options[selected_priority_filter],
    )
    opportunity_map = build_customer_opportunity_map(repo, filtered_customers)
    customers_df = customers_to_dataframe(filtered_customers, locale, repo, opportunity_map)
    st.caption(t(locale, "customer.showing_count", filtered=len(filtered_customers), total=len(customers)))

    # --- CRM Summary Table: max 6 core columns ---
    core_cols = ["customer", "stage", "agent_id", "opportunity_score", "priority", "next_meeting_date"]
    available_core = [c for c in core_cols if c in customers_df.columns]
    render_simple_table(customers_df[available_core], locale)

    # --- Expander: AI details for each customer ---
    expander_cols = ["customer", "opportunity_reason", "next_best_action", "suggested_message", "followup_deadline", "notes"]
    available_expander = [c for c in expander_cols if c in customers_df.columns]
    if not customers_df.empty and available_expander:
        with st.expander(t(locale, "crm.expander_ai_details")):
            render_simple_table(customers_df[available_expander], locale)

    render_opportunity_basis(opportunity_map, locale)

    # --- Customer 360 View ---
    if filtered_customers:
        render_customer_360(repo, filtered_customers, locale, user)

    with st.form("customer_form"):
        st.markdown(t(locale, "customer.add"))
        name = st.text_input(t(locale, "customer.name"))
        phone = st.text_input(t(locale, "customer.phone"))
        stage_labels = {translated_stage(locale, stage.value): stage.value for stage in CustomerStage}
        selected_stage = st.selectbox(t(locale, "customer.stage"), list(stage_labels.keys()), key=f"customer_stage_select_{user.id}")
        stage = stage_labels[selected_stage]
        next_meeting = st.date_input(t(locale, "customer.next_meeting_date"), value=date.today())
        notes = st.text_area(t(locale, "customer.notes"))
        agents = visible_agents(repo, user)
        agent_options = {f"{agent.name} ({agent.email})": agent for agent in agents}
        selected_agent_label = None
        if user.role != UserRole.AGENT and agent_options:
            selected_agent_label = st.selectbox(t(locale, "customer.agent"), list(agent_options.keys()), key=f"customer_agent_select_{user.id}")
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
        selected_customer = customer_map[st.selectbox(t(locale, "customer.customer"), list(customer_map.keys()), key=f"customer_followup_select_{user.id}")]
        with st.form("followup_form"):
            note = st.text_area(t(locale, "customer.followup_note"))
            next_action = st.text_input(t(locale, "customer.next_action"))
            save_followup = st.form_submit_button(t(locale, "customer.save_followup"))
        if save_followup:
            service.add_followup(TENANT_ID, selected_customer.id, user.id, note, next_action)
            st.success(t(locale, "customer.followup_saved"))
            st.rerun()
        render_simple_table(
            pd.DataFrame(
                [
                    {
                        "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
                        "agent_id": agent_display_name(repo, f.agent_id),
                        "note": f.note,
                        "next_action": f.next_action,
                    }
                    for f in service.customer_history(TENANT_ID, selected_customer.id)
                ],
                columns=["created_at", "agent_id", "note", "next_action"],
            ),
            locale,
        )
    recent_followups_df = visible_followups_to_dataframe(repo, user, locale)
    st.subheader(t(locale, "customer.recent_followups"))
    if recent_followups_df.empty:
        st.info(t(locale, "customer.no_recent_followups"))
    else:
        render_simple_table(recent_followups_df, locale)


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
    log_agent_col, log_date_col, log_issue_col = st.columns(3)
    log_agent_options = {t(locale, "filter.all"): None}
    log_agent_options.update({agent_display_name(repo, agent.id): agent.id for agent in visible_agents(repo, user)})
    selected_log_agent = log_agent_col.selectbox(t(locale, "filter.agent"), list(log_agent_options.keys()), key=f"daily_agent_filter_{user.id}")
    date_range_options = {
        t(locale, "filter.all"): "all",
        t(locale, "filter.today"): "today",
        t(locale, "filter.last_7_days"): "last_7_days",
        t(locale, "filter.last_30_days"): "last_30_days",
    }
    selected_log_range = log_date_col.selectbox(t(locale, "filter.date_range"), list(date_range_options.keys()), key=f"daily_date_filter_{user.id}")
    issue_options = {
        t(locale, "filter.all"): "all",
        t(locale, "filter.low_activity"): "low_activity",
        t(locale, "filter.low_closing"): "low_closing",
    }
    selected_log_issue = log_issue_col.selectbox(t(locale, "filter.activity_issue"), list(issue_options.keys()), key=f"daily_issue_filter_{user.id}")
    logs = filter_daily_logs(
        logs,
        log_agent_options[selected_log_agent],
        date_range_options[selected_log_range],
        issue_options[selected_log_issue],
    )
    logs_df = daily_logs_to_dataframe(logs)
    render_simple_table(logs_df.drop(columns=["id", "created_at"]), locale)


def render_customer_csv_import(repo: SQLiteGroupTrainingRepository, user, locale: str) -> None:
    st.subheader(t(locale, "customer.import_csv"))
    import_agents = visible_agents(repo, user)
    target_agent_id = user.id
    if user.role != UserRole.AGENT and import_agents:
        agent_options = {f"{agent.name} ({agent.email})": agent.id for agent in import_agents}
        selected_agent_label = st.selectbox(t(locale, "customer.import_agent"), list(agent_options.keys()), key=f"customer_import_agent_{user.id}")
        target_agent_id = agent_options[selected_agent_label]
    uploaded_csv = st.file_uploader(t(locale, "customer.upload_csv"), type=["csv"], key="customer_csv_import")
    if uploaded_csv:
        try:
            csv_dataframe = pd.read_csv(uploaded_csv)
            preview_dataframe = normalize_customer_import_dataframe(csv_dataframe)
            st.session_state["customer_csv_import_preview"] = preview_dataframe
            st.session_state["customer_csv_import_agent_id"] = target_agent_id
            st.markdown(t(locale, "customer.import_preview"))
            render_simple_table(
                preview_dataframe.assign(next_meeting_date=preview_dataframe["next_meeting_date"].astype(str)),
                locale,
            )
            if preview_dataframe.empty:
                st.warning(t(locale, "customer.import_no_valid_rows"))
        except Exception as exc:
            st.error(t(locale, "customer.import_failed", error=str(exc)))
    preview_dataframe = st.session_state.get("customer_csv_import_preview")
    if preview_dataframe is not None:
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button(t(locale, "customer.confirm_import"), disabled=preview_dataframe.empty, key=f"customer_confirm_import_{user.id}"):
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
        if cancel_col.button(t(locale, "customer.cancel_import"), key=f"customer_cancel_import_{user.id}"):
            st.session_state.pop("customer_csv_import_preview", None)
            st.session_state.pop("customer_csv_import_agent_id", None)
            st.rerun()


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
            key=f"ocr_customer_stage_{user.id}",
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
            selected_agent_label = st.selectbox(t(locale, "customer.agent"), list(agent_options.keys()), key=f"ocr_customer_agent_{user.id}")
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
            selected_agent_label = st.selectbox(t(locale, "daily.agent"), list(agent_options.keys()), key=f"ocr_daily_agent_{user.id}")
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
            key=f"ocr_followup_customer_{user.id}",
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
    repo = get_repo()
    st.subheader(t(locale, "ocr.title"))
    st.caption(t(locale, "ocr.description"))
    if st.session_state.pop("ocr_flash_success", False):
        st.success(t(locale, "ocr.save_success"))

    st.subheader(t(locale, "data.import_section"))
    st.caption(t(locale, "data.import_description"))
    with st.expander(t(locale, "customer.import_csv")):
        render_customer_csv_import(repo, user, locale)

    st.subheader(t(locale, "data.export_section"))
    st.caption(t(locale, "data.export_description"))
    visible_agent_id = user.id if user.role == UserRole.AGENT else None
    customers_df = customers_to_dataframe(repo.list_customers(TENANT_ID, agent_id=visible_agent_id), locale, repo)
    logs_df = daily_logs_to_dataframe(repo.list_logs(TENANT_ID, agent_id=visible_agent_id))
    export_customer_col, export_daily_col = st.columns(2)
    with export_customer_col:
        render_csv_download(t(locale, "customer.export_csv"), customers_df, "buildway_customers.csv", "customers_csv_upload_page", locale)
    with export_daily_col:
        render_csv_download(t(locale, "daily.export_csv"), logs_df, "buildway_daily_logs.csv", "daily_logs_csv_upload_page", locale)

    st.subheader(t(locale, "data.document_section"))
    st.caption(t(locale, "data.document_description"))
    uploaded_file = st.file_uploader(t(locale, "ocr.upload_image"), type=["png", "jpg", "jpeg", "pdf", "csv", "xlsx"], key=f"ocr_upload_file_{user.id}")
    data_type_options = ocr_data_type_options(locale)
    selected_data_type_label = st.selectbox(t(locale, "ocr.data_type"), list(data_type_options.keys()), key=f"ocr_data_type_{user.id}")
    selected_data_type = data_type_options[selected_data_type_label]

    file_bytes = b""
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        st.info(t(locale, "data.demo_mode"))
        file_info_df = pd.DataFrame(
            [
                {
                    "file_name": uploaded_file.name,
                    "file_size": len(file_bytes),
                    "file_type": uploaded_file.type or Path(uploaded_file.name).suffix.lower().lstrip("."),
                }
            ]
        )
        render_simple_table(file_info_df, locale)
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            st.markdown(t(locale, "ocr.preview"))
            st.image(file_bytes, use_container_width=True)
        else:
            st.info(t(locale, "ocr.non_image_received"))

    if st.button(t(locale, "ocr.start_extract"), disabled=not bool(file_bytes), key=f"ocr_start_extract_{user.id}"):
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
    agent_col, stage_col, priority_col = st.columns(3)
    agent_options = {t(locale, "filter.all"): None}
    agent_options.update({agent_display_name(repo, agent.id): agent.id for agent in visible_agents(repo, user)})
    selected_agent = agent_col.selectbox(t(locale, "filter.agent"), list(agent_options.keys()), key=f"schedule_agent_filter_{user.id}")
    stage_options = {t(locale, "customer.stage_all"): None}
    stage_options.update({translated_stage(locale, stage.value): stage.value for stage in CustomerStage})
    selected_stage = stage_col.selectbox(t(locale, "customer.stage_filter"), list(stage_options.keys()), key=f"schedule_stage_filter_{user.id}")
    priority_options = {
        t(locale, "filter.all"): "all",
        t(locale, "schedule.priority_high"): "high",
        t(locale, "schedule.priority_medium"): "medium",
        t(locale, "schedule.priority_low"): "low",
    }
    selected_priority = priority_col.selectbox(t(locale, "filter.ai_priority"), list(priority_options.keys()), key=f"schedule_priority_filter_{user.id}")
    customers = filter_customers(
        customers,
        stage=stage_options[selected_stage],
        agent_id=agent_options[selected_agent],
        priority=priority_options[selected_priority],
    )
    opportunity_map = build_customer_opportunity_map(repo, customers)
    schedule_df = today_schedule_to_dataframe(customers, locale, repo, opportunity_map)
    st.info(t(locale, "schedule.today_followup_note"))
    st.caption(t(locale, "schedule.showing_count", total=len(customers)))
    
    # --- Today Schedule Summary: max 6 core columns ---
    core_schedule_cols = ["customer", "stage", "agent_id", "phone", "opportunity_score", "priority"]
    available_schedule_core = [c for c in core_schedule_cols if c in schedule_df.columns]
    render_simple_table(schedule_df[available_schedule_core], locale)
    
    # --- Expander: AI details and notes ---
    expander_schedule_cols = ["customer", "opportunity_reason", "contact_method", "next_best_action", "suggested_message", "notes", "today_meeting"]
    available_schedule_expander = [c for c in expander_schedule_cols if c in schedule_df.columns]
    if not schedule_df.empty and available_schedule_expander:
        with st.expander(t(locale, "crm.expander_ai_details")):
            render_simple_table(schedule_df[available_schedule_expander], locale)
    
    render_opportunity_basis(opportunity_map, locale)
    st.info(t(locale, schedule_recommendation_key(customers)))
    pending_followups_df = visible_followups_to_dataframe(repo, user, locale, pending_only=True)
    st.subheader(t(locale, "schedule.pending_followups"))
    if pending_followups_df.empty:
        st.info(t(locale, "schedule.no_pending_followups"))
    else:
        render_simple_table(pending_followups_df, locale)


def render_demo_ai_insights(repo: SQLiteGroupTrainingRepository, user, locale: str) -> None:
    agents = report_agents(repo, user)
    agent_ids = {agent.id for agent in agents}
    visible_agent_id = user.id if user.role == UserRole.AGENT else None
    customers = repo.list_customers(TENANT_ID, agent_id=visible_agent_id)
    logs = repo.list_logs(TENANT_ID, agent_id=visible_agent_id)
    reviews = repo.list_reviews(TENANT_ID, agent_id=visible_agent_id)
    scores = repo.list_closing_scores(TENANT_ID, agent_id=visible_agent_id)
    if user.role != UserRole.AGENT:
        customers = [customer for customer in customers if customer.agent_id in agent_ids]
        logs = [log for log in logs if log.agent_id in agent_ids]
        reviews = [review for review in reviews if review.agent_id in agent_ids]
        scores = [score for score in scores if score.agent_id in agent_ids]
    insights = generate_demo_ai_insights(user, agents, customers, logs, reviews, scores)
    st.subheader(t(locale, "training.demo_insights"))
    if insights["today_outreach"] or insights["today_meetings"]:
        st.info(
            t(
                locale,
                "training.today_recommendation",
                outreach=insights["today_outreach"],
                meetings=insights["today_meetings"],
            )
        )
    else:
        st.info(t(locale, "training.today_recommendation_empty"))

    insight_col_1, insight_col_2 = st.columns(2)
    high_potential_df = customers_to_dataframe(insights["high_potential_customers"], locale, repo)
    insight_col_1.markdown(t(locale, "training.high_potential_customers"))
    render_simple_table(high_potential_df.drop(columns=["id", "created_at"]), locale, insight_col_1)

    followup_df = customers_to_dataframe(insights["followup_customers"], locale, repo)
    insight_col_2.markdown(t(locale, "training.followup_customers"))
    render_simple_table(followup_df.drop(columns=["id", "created_at"]), locale, insight_col_2)

    if user.role == UserRole.AGENT:
        st.caption(t(locale, "training.agent_activity_reminder", risk=translated_risk(locale, insights["latest_risk"])))
    else:
        st.caption(
            t(
                locale,
                "training.manager_team_recommendation",
                low_active=insights["low_active_agent_count"],
                risk_agents=len(insights["risk_agent_ids"]),
            )
        )


def ai_training_page(user, locale: str) -> None:
    repo = get_repo()
    st.subheader(t(locale, "training.title"))
    render_scoring_basis(locale)
    render_demo_ai_insights(repo, user, locale)
    if user.role == UserRole.AGENT:
        reviews = repo.list_reviews(TENANT_ID, agent_id=user.id)
        logs = repo.list_logs(TENANT_ID, agent_id=user.id)
    else:
        visible_agent_ids = {agent.id for agent in report_agents(repo, user)}
        reviews = [review for review in repo.list_reviews(TENANT_ID) if review.agent_id in visible_agent_ids]
        logs = [log for log in repo.list_logs(TENANT_ID) if log.agent_id in visible_agent_ids]
    review_agent_col, review_risk_col, review_date_col = st.columns(3)
    review_agent_options = {t(locale, "filter.all"): None}
    review_agent_options.update({agent_display_name(repo, agent.id): agent.id for agent in report_agents(repo, user)})
    selected_review_agent = review_agent_col.selectbox(t(locale, "filter.agent"), list(review_agent_options.keys()), key=f"training_agent_filter_{user.id}")
    risk_options = {
        t(locale, "filter.all"): "all",
        t(locale, "risk.High"): "High",
        t(locale, "risk.Medium"): "Medium",
        t(locale, "risk.Low"): "Low",
    }
    selected_review_risk = review_risk_col.selectbox(t(locale, "filter.risk"), list(risk_options.keys()), key=f"training_risk_filter_{user.id}")
    date_range_options = {
        t(locale, "filter.all"): "all",
        t(locale, "filter.today"): "today",
        t(locale, "filter.last_7_days"): "last_7_days",
        t(locale, "filter.last_30_days"): "last_30_days",
    }
    selected_review_range = review_date_col.selectbox(t(locale, "filter.date_range"), list(date_range_options.keys()), key=f"training_date_filter_{user.id}")
    reviews = filter_reviews(
        reviews,
        review_agent_options[selected_review_agent],
        risk_options[selected_review_risk],
        date_range_options[selected_review_range],
    )
    if review_agent_options[selected_review_agent]:
        logs = [log for log in logs if log.agent_id == review_agent_options[selected_review_agent]]
    logs = filter_by_date_range(logs, "activity_date", date_range_options[selected_review_range])
    filtered_agents = [agent for agent in report_agents(repo, user) if not review_agent_options[selected_review_agent] or agent.id == review_agent_options[selected_review_agent]]
    plan_scores = [] if user.role == UserRole.AGENT else repo.list_closing_scores(TENANT_ID)
    plans = build_visible_agent_coaching_plans(repo, filtered_agents, logs, reviews, plan_scores)
    st.subheader(t(locale, "sales.performance_analysis"))
    render_simple_table(sales_performance_to_dataframe(plans, locale), locale)
    log_index = logs_by_agent_and_date(logs)
    render_simple_table(
        pd.DataFrame(
            [
                {
                    "date": r.review_date,
                    "agent_id": agent_display_name(repo, r.agent_id),
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
    )
    if user.role == UserRole.AGENT:
        st.info(t(locale, "training.hidden_score_agent_info"))
    else:
        st.subheader(t(locale, "coaching.title"))
        # --- Coaching Summary Table: max 4 core columns ---
        coaching_df = coaching_plan_to_dataframe(plans, locale)
        core_coaching_cols = ["agent_id", "hidden_score", "risk", "priority"]
        available_coaching_core = [c for c in core_coaching_cols if c in coaching_df.columns]
        if not available_coaching_core:
            available_coaching_core = ["agent_id", "hidden_score", "risk", "performance_score"]
        render_simple_table(coaching_df[available_coaching_core], locale)
        
        # --- Expander: Coaching Plan Details ---
        expander_coaching_cols = ["agent_id", "coaching_issue", "root_cause", "training_focus", "next_action", "why_this_coaching", "manager_note", "target_metric", "target_date", "expected_improvement"]
        available_coaching_expander = [c for c in expander_coaching_cols if c in coaching_df.columns]
        if not coaching_df.empty and available_coaching_expander:
            with st.expander(t(locale, "coaching.expander_plan_details")):
                render_simple_table(coaching_df[available_coaching_expander], locale)


def manager_dashboard_page(user, locale: str) -> None:
    if user.role == UserRole.AGENT:
        st.warning(t(locale, "dashboard.agent_blocked"))
        return
    repo = get_repo()
    render_demo_dataset_controls(repo, user, locale)
    manager_id = user.id if user.role == UserRole.MANAGER else "mgr_001"
    dashboard = DashboardService(repo).manager_dashboard(TENANT_ID, manager_id, user.role)
    if user.role != UserRole.AGENT and not dashboard["agents"]:
        agents = report_agents(repo, user)
        agent_ids = {agent.id for agent in agents}
        dashboard = {
            "agents": agents,
            "daily_logs": [log for log in repo.list_logs(TENANT_ID) if log.agent_id in agent_ids],
            "reviews": [review for review in repo.list_reviews(TENANT_ID) if review.agent_id in agent_ids],
            "closing_scores": [score for score in repo.list_closing_scores(TENANT_ID) if score.agent_id in agent_ids],
            "high_risk_agent_ids": [
                review.agent_id
                for review in repo.list_reviews(TENANT_ID)
                if review.agent_id in agent_ids and review.risk_level == "High"
            ],
        }
    filter_agent_col, filter_stage_col, filter_score_col, filter_priority_col = st.columns(4)
    dashboard_agent_options = {t(locale, "filter.all"): None}
    dashboard_agent_options.update({agent_display_name(repo, agent.id): agent.id for agent in dashboard["agents"]})
    selected_dashboard_agent = filter_agent_col.selectbox(
        t(locale, "filter.agent"),
        list(dashboard_agent_options.keys()),
        key=f"dashboard_agent_filter_{user.id}",
    )
    stage_options = {t(locale, "customer.stage_all"): None}
    stage_options.update({translated_stage(locale, stage.value): stage.value for stage in CustomerStage})
    selected_dashboard_stage = filter_stage_col.selectbox(
        t(locale, "customer.stage_filter"),
        list(stage_options.keys()),
        key=f"dashboard_stage_filter_{user.id}",
    )
    score_risk_options = {
        t(locale, "filter.all"): "all",
        t(locale, "hidden_score.risk_critical"): "critical",
        t(locale, "hidden_score.risk_high"): "high",
        t(locale, "hidden_score.risk_medium"): "medium",
        t(locale, "hidden_score.risk_low"): "low",
    }
    selected_score_risk = filter_score_col.selectbox(
        t(locale, "filter.hidden_score_risk"),
        list(score_risk_options.keys()),
        key=f"dashboard_score_risk_filter_{user.id}",
    )
    priority_options = {
        t(locale, "filter.all"): "all",
        t(locale, "schedule.priority_high"): "high",
        t(locale, "schedule.priority_medium"): "medium",
        t(locale, "schedule.priority_low"): "low",
    }
    selected_dashboard_priority = filter_priority_col.selectbox(
        t(locale, "filter.ai_priority"),
        list(priority_options.keys()),
        key=f"dashboard_priority_filter_{user.id}",
    )
    selected_dashboard_agent_id = dashboard_agent_options[selected_dashboard_agent]
    if selected_dashboard_agent_id:
        dashboard["agents"] = [agent for agent in dashboard["agents"] if agent.id == selected_dashboard_agent_id]
        dashboard["daily_logs"] = [log for log in dashboard["daily_logs"] if log.agent_id == selected_dashboard_agent_id]
        dashboard["reviews"] = [review for review in dashboard["reviews"] if review.agent_id == selected_dashboard_agent_id]
        dashboard["closing_scores"] = [score for score in dashboard["closing_scores"] if score.agent_id == selected_dashboard_agent_id]
        dashboard["high_risk_agent_ids"] = [agent_id for agent_id in dashboard["high_risk_agent_ids"] if agent_id == selected_dashboard_agent_id]
    dashboard["closing_scores"] = filter_scores(
        dashboard["closing_scores"],
        risk_band=score_risk_options[selected_score_risk],
    )
    team_ids = {agent.team_id for agent in dashboard["agents"] if agent.team_id}
    customers = [customer for team_id in team_ids for customer in repo.list_customers(TENANT_ID, team_id=team_id)]
    customers = filter_customers(
        customers,
        stage=stage_options[selected_dashboard_stage],
        agent_id=selected_dashboard_agent_id,
        priority=priority_options[selected_dashboard_priority],
    )
    metrics = generate_demo_dashboard_metrics(
        dashboard["agents"],
        customers,
        dashboard["daily_logs"],
        dashboard["reviews"],
        dashboard["closing_scores"],
    )
    opportunity_map = build_customer_opportunity_map(repo, customers)
    coaching_plans = build_visible_agent_coaching_plans(
        repo,
        dashboard["agents"],
        dashboard["daily_logs"],
        dashboard["reviews"],
        dashboard["closing_scores"],
    )
    st.subheader(t(locale, "dashboard.title"))
    render_scoring_basis(locale)
    c1, c2, c3, c4 = st.columns(4)
    metric_rows = dashboard_metric_rows(metrics)
    for column, (label_key, value) in zip([c1, c2, c3, c4], metric_rows[:4]):
        column.metric(t(locale, label_key), value)
    c5, c6, c7, c8 = st.columns(4)
    for column, (label_key, value) in zip([c5, c6, c7, c8], metric_rows[4:]):
        column.metric(t(locale, label_key), value)

    render_manager_insight_section(
        repo,
        locale,
        dashboard["agents"],
        customers,
        dashboard["daily_logs"],
        dashboard["closing_scores"],
        coaching_plans,
        opportunity_map,
    )

    chart_col_1, chart_col_2 = st.columns(2)
    logs_df = daily_logs_to_dataframe(dashboard["daily_logs"])
    if not logs_df.empty:
        chart_col_1.markdown(t(locale, "dashboard.daily_activity_trend"))
        chart_col_1.altair_chart(activity_chart(logs_df, locale), use_container_width=True)
    else:
        chart_col_1.info(t(locale, "dashboard.no_daily_log_data"))

    if customers:
        chart_col_2.markdown(t(locale, "dashboard.customers_by_stage"))
        chart_col_2.altair_chart(stage_chart(customers, locale), use_container_width=True)
    else:
        chart_col_2.info(t(locale, "dashboard.no_customer_data"))

    team_col, score_col = st.columns(2)
    team_col.markdown(t(locale, "dashboard.team_downline"))
    render_simple_table(
        pd.DataFrame(
            [{"agent_id": agent_display_name(repo, a.id), "name": a.name, "email": a.email, "team_id": a.team_id} for a in dashboard["agents"]],
            columns=["agent_id", "name", "email", "team_id"],
        ),
        locale,
        team_col,
    )
    team_col.markdown(t(locale, "dashboard.top_agents"))
    render_simple_table(top_agents_to_dataframe(repo, metrics["top_agents"]), locale, team_col)
    team_col.markdown(t(locale, "dashboard.risk_agents"))
    render_simple_table(risk_agents_to_dataframe(repo, metrics["risk_agent_ids"], locale), locale, team_col)
    team_col.markdown(t(locale, "coaching.title"))
    # --- Dashboard Coaching Summary: 4 core columns ---
    dash_coaching_df = coaching_plan_to_dataframe(coaching_plans, locale)
    dash_core_cols = ["agent_id", "hidden_score", "risk", "performance_score"]
    dash_available_core = [c for c in dash_core_cols if c in dash_coaching_df.columns]
    render_simple_table(dash_coaching_df[dash_available_core], locale, team_col)
    # --- Expander: full coaching plan ---
    dash_expander_cols = ["agent_id", "coaching_issue", "root_cause", "training_focus", "next_action", "manager_note", "target_metric", "target_date", "expected_improvement"]
    dash_available_expander = [c for c in dash_expander_cols if c in dash_coaching_df.columns]
    if not dash_coaching_df.empty and dash_available_expander:
        with team_col.expander(t(locale, "coaching.expander_plan_details")):
            render_simple_table(dash_coaching_df[dash_available_expander], locale)

    score_col.markdown(t(locale, "dashboard.hidden_closing_score"))
    scores_df = pd.DataFrame(
        [
            {
                "date": s.score_date.isoformat(),
                "agent_id": agent_display_name(repo, s.agent_id),
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
        render_simple_table(score_summary_df, locale, score_col)
        with score_col.expander(t(locale, "hidden_score.breakdown_title")) as breakdown_container:
            render_simple_table(hidden_score_breakdown_dataframe(dashboard["closing_scores"], dashboard["daily_logs"], locale), locale, breakdown_container)
    render_simple_table(scores_df, locale, score_col)


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
    selected_page = st.sidebar.radio(t(locale, "nav.label"), list(pages.keys()), key=f"sidebar_nav_{user.id}")
    pages[selected_page](user, locale)


if __name__ == "__main__":
    main()
