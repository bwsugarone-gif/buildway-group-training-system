import json
from pathlib import Path

from apps.streamlit_group_training.services.demo_dataset_service import (
    DEMO_AGENT_PREFIX,
    DEMO_CUSTOMER_PREFIX,
    DEMO_LOG_PREFIX,
    generate_demo_dashboard_metrics,
    reset_demo_dataset,
    seed_demo_dataset,
)
from verticals.group_training.services.dashboard_service import DashboardService
from verticals.group_training.services.repository import build_in_memory_repository
from verticals.group_training.services.sqlite_repository import DEFAULT_TEAM_ID
from verticals.group_training.models import UserRole


TENANT_ID = "tenant_buildway_demo"
I18N_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit_group_training" / "i18n"


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
