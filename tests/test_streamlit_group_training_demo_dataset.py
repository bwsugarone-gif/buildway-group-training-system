import json
import inspect
from pathlib import Path

from streamlit.testing.v1 import AppTest

from apps.streamlit_group_training.app import report_agents, render_demo_dataset_controls
from apps.streamlit_group_training.services.demo_dataset_service import (
    DEMO_AGENT_PREFIX,
    DEMO_CUSTOMER_PREFIX,
    DEMO_LOG_PREFIX,
    generate_demo_dashboard_metrics,
    reset_demo_dataset,
    seed_demo_dataset,
)
from verticals.group_training.models import User, UserRole
from verticals.group_training.services.dashboard_service import DashboardService
from verticals.group_training.services.repository import build_in_memory_repository
from verticals.group_training.services.sqlite_repository import DEFAULT_TEAM_ID


TENANT_ID = "tenant_buildway_demo"
I18N_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit_group_training" / "i18n"
APP_PATH = "apps/streamlit_group_training/app.py"


def test_demo_dataset_can_seed_20_agents():
    repo = build_in_memory_repository()

    counts = seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    demo_agents = [user for user in repo.list_users(TENANT_ID) if user.id.startswith(DEMO_AGENT_PREFIX)]

    assert counts["agents"] == 20
    assert len(demo_agents) == 20


def test_demo_dataset_can_seed_200_customers():
    repo = build_in_memory_repository()

    counts = seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    demo_customers = [customer for customer in repo.list_customers(TENANT_ID) if customer.id.startswith(DEMO_CUSTOMER_PREFIX)]

    assert counts["customers"] == 200
    assert len(demo_customers) == 200


def test_demo_dataset_can_seed_500_activity_logs_and_reviews():
    repo = build_in_memory_repository()

    counts = seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    demo_logs = [log for log in repo.list_logs(TENANT_ID) if log.id.startswith(DEMO_LOG_PREFIX)]
    dashboard = DashboardService(repo).manager_dashboard(TENANT_ID, "mgr_001", UserRole.MANAGER)

    assert counts["daily_logs"] == 500
    assert len(demo_logs) == 500
    assert len([review for review in dashboard["reviews"] if review.agent_id.startswith(DEMO_AGENT_PREFIX)]) == 500
    assert len([score for score in dashboard["closing_scores"] if score.agent_id.startswith(DEMO_AGENT_PREFIX)]) == 500


def test_demo_dataset_creates_ai_training_reviews():
    repo = build_in_memory_repository()

    seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")

    assert len([review for review in repo.list_reviews(TENANT_ID) if review.agent_id.startswith(DEMO_AGENT_PREFIX)]) == 500


def test_reset_demo_dataset_removes_only_demo_records():
    repo = build_in_memory_repository()
    seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")

    reset_demo_dataset(repo, TENANT_ID)

    assert [user for user in repo.list_users(TENANT_ID) if user.id.startswith(DEMO_AGENT_PREFIX)] == []
    assert [customer for customer in repo.list_customers(TENANT_ID) if customer.id.startswith(DEMO_CUSTOMER_PREFIX)] == []
    assert [log for log in repo.list_logs(TENANT_ID) if log.id.startswith(DEMO_LOG_PREFIX)] == []
    assert repo.get_user(TENANT_ID, "agt_001") is not None


def test_manager_dashboard_metrics_are_generated_from_demo_dataset():
    repo = build_in_memory_repository()
    seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    dashboard = DashboardService(repo).manager_dashboard(TENANT_ID, "mgr_001", UserRole.MANAGER)
    customers = repo.list_customers(TENANT_ID, team_id=DEFAULT_TEAM_ID)

    metrics = generate_demo_dashboard_metrics(
        dashboard["agents"],
        customers,
        dashboard["daily_logs"],
        dashboard["reviews"],
        dashboard["closing_scores"],
    )

    assert metrics["team_total_customers"] == 200
    assert metrics["today_activity_count"] > 0
    assert metrics["weekly_followup_count"] > 0
    assert metrics["overdue_followup_count"] > 0
    assert metrics["high_potential_customer_count"] > 0
    assert metrics["low_active_agent_count"] > 0
    assert metrics["hidden_score_average"] > 0
    assert len(metrics["top_agents"]) == 5
    assert metrics["risk_agent_ids"]


def test_report_agents_lets_manager_see_demo_team_reviews_with_fallback():
    repo = build_in_memory_repository()
    seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    manager = User(TENANT_ID, "mgr_new", "New Manager", "new.manager@buildway.demo", UserRole.MANAGER, DEFAULT_TEAM_ID)
    repo.add_user(manager)

    agent_ids = {agent.id for agent in report_agents(repo, manager)}
    visible_reviews = [review for review in repo.list_reviews(TENANT_ID) if review.agent_id in agent_ids]

    assert len(agent_ids) >= 20
    assert len(visible_reviews) == 500


def test_agent_only_sees_own_ai_reviews():
    repo = build_in_memory_repository()
    seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    agent = repo.get_user(TENANT_ID, f"{DEMO_AGENT_PREFIX}001")

    agent_ids = {visible_agent.id for visible_agent in report_agents(repo, agent)}
    visible_reviews = [review for review in repo.list_reviews(TENANT_ID) if review.agent_id in agent_ids]

    assert agent_ids == {f"{DEMO_AGENT_PREFIX}001"}
    assert len(visible_reviews) == 25


def test_render_demo_dataset_controls_uses_unique_keys():
    source = inspect.getsource(render_demo_dataset_controls)

    assert "dashboard_demo_confirm_" in source
    assert "dashboard_demo_load_" in source
    assert "dashboard_demo_reset_" in source


def test_dashboard_page_does_not_raise_duplicate_element_id():
    at = AppTest.from_file(APP_PATH)
    at.session_state["gt_locale"] = "en"
    at.run(timeout=10)
    at.text_input[0].set_value("manager@buildway.demo")
    at.text_input[1].set_value("Manager123!")
    at.button[0].click()
    at.run(timeout=10)

    at.radio[0].set_value("Manager Dashboard")
    at.run(timeout=10)

    assert not at.exception


def test_demo_i18n_keys_match():
    zh = json.loads((I18N_DIR / "zh_HK.json").read_text(encoding="utf-8"))
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))

    assert set(zh) == set(en)
    for key in [
        "demo.load_dataset",
        "demo.reset_dataset",
        "dashboard.team_total_customers",
        "dashboard.today_activity_count",
        "dashboard.top_agents",
        "training.demo_insights",
    ]:
        assert key in zh
        assert key in en


def test_no_question_mark_garbage_in_zh_demo_insight_keys():
    zh = json.loads((I18N_DIR / "zh_HK.json").read_text(encoding="utf-8"))
    keys = [
        key
        for key in zh
        if key.startswith("demo.")
        or key in {
            "training.demo_insights",
            "training.today_recommendation",
            "training.today_recommendation_empty",
            "training.high_potential_customers",
            "training.followup_customers",
            "training.agent_activity_reminder",
            "training.manager_team_recommendation",
        }
    ]

    assert keys
    assert all("???" not in zh[key] for key in keys)
    assert zh["training.demo_insights"] == "AI 培訓洞察"
