from datetime import date

from verticals.group_training.models import CustomerStage, UserRole
from verticals.group_training.agents.closing_agent import calculate_hidden_closing_score
from verticals.group_training.agents.training_agent import review_daily_performance
from verticals.group_training.services.auth_service import AuthService
from verticals.group_training.services.customer_service import CustomerService
from verticals.group_training.services.daily_log_service import DailyLogService
from verticals.group_training.services.dashboard_service import DashboardService
from verticals.group_training.services.repository import build_in_memory_repository
from verticals.group_training.services.sqlite_repository import SQLiteGroupTrainingRepository


def test_customer_and_followup_history_are_tenant_scoped():
    repo = build_in_memory_repository()
    service = CustomerService(repo)

    customer = service.create_customer(
        "tenant_buildway_demo",
        "team_alpha",
        "agt_001",
        "Test Customer",
        CustomerStage.WARM,
    )
    service.add_followup("tenant_buildway_demo", customer.id, "agt_001", "Called customer.")

    assert len(service.customer_history("tenant_buildway_demo", customer.id)) == 1
    assert service.customer_history("other_tenant", customer.id) == []


def test_daily_log_generates_review_and_hidden_score_for_manager():
    repo = build_in_memory_repository()
    log_service = DailyLogService(repo)
    log_service.create_log(
        "tenant_buildway_demo",
        "team_alpha",
        "agt_001",
        date.today(),
        call_count=20,
        whatsapp_count=10,
        appointment_count=3,
        meeting_count=2,
        closing_count=1,
    )

    dashboard = DashboardService(repo)
    dashboard.generate_reviews_for_date("tenant_buildway_demo", date.today())
    data = dashboard.manager_dashboard("tenant_buildway_demo", "mgr_001", UserRole.MANAGER)

    assert data["reviews"]
    assert data["closing_scores"]
    assert data["closing_scores"][0].hidden_score > 0


def test_agent_role_does_not_receive_hidden_closing_score():
    repo = build_in_memory_repository()
    log_service = DailyLogService(repo)
    log_service.create_log("tenant_buildway_demo", "team_alpha", "agt_001", date.today())
    dashboard = DashboardService(repo)
    dashboard.generate_reviews_for_date("tenant_buildway_demo", date.today())

    data = dashboard.manager_dashboard("tenant_buildway_demo", "mgr_001", UserRole.AGENT)

    assert data["closing_scores"] == []


def test_sqlite_customer_persists_after_repository_refresh(tmp_path):
    db_path = tmp_path / "group_training.sqlite3"
    repo = SQLiteGroupTrainingRepository(db_path)
    service = CustomerService(repo)

    service.create_customer(
        "tenant_buildway_demo",
        "team_alpha",
        "agt_001",
        "Persistent Customer",
        CustomerStage.HOT,
    )

    refreshed_repo = SQLiteGroupTrainingRepository(db_path)
    customers = refreshed_repo.list_customers("tenant_buildway_demo", agent_id="agt_001")

    assert [customer.name for customer in customers] == ["Persistent Customer"]


def test_sqlite_daily_log_persists_after_repository_refresh(tmp_path):
    db_path = tmp_path / "group_training.sqlite3"
    repo = SQLiteGroupTrainingRepository(db_path)
    log_service = DailyLogService(repo)

    log_service.create_log(
        "tenant_buildway_demo",
        "team_alpha",
        "agt_001",
        date.today(),
        call_count=7,
        whatsapp_count=5,
        appointment_count=1,
        meeting_count=1,
        closing_count=0,
    )

    refreshed_repo = SQLiteGroupTrainingRepository(db_path)
    logs = refreshed_repo.list_logs("tenant_buildway_demo", agent_id="agt_001")

    assert len(logs) == 1
    assert logs[0].call_count == 7
    assert logs[0].whatsapp_count == 5


def test_daily_log_upsert_replaces_same_agent_same_date(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "upsert.sqlite3")
    log_service = DailyLogService(repo)
    log_date = date.today()

    first = log_service.create_log("tenant_buildway_demo", "team_alpha", "agt_001", log_date, 1, 1, 0, 0, 0, "old")
    second = log_service.create_log("tenant_buildway_demo", "team_alpha", "agt_001", log_date, 9, 8, 1, 1, 1, "latest")

    logs = repo.list_logs("tenant_buildway_demo", activity_date=log_date, agent_id="agt_001")
    assert first.id == second.id
    assert len(logs) == 1
    assert logs[0].call_count == 9
    assert logs[0].notes == "latest"


def test_daily_review_and_hidden_score_keep_latest_same_day(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "review_score_latest.sqlite3")
    log_service = DailyLogService(repo)
    log_date = date.today()
    first = log_service.create_log("tenant_buildway_demo", "team_alpha", "agt_001", log_date, 1, 1, 0, 0, 0, "old")
    repo.add_review(review_daily_performance(first))
    repo.add_closing_score(calculate_hidden_closing_score(first))
    latest = log_service.create_log("tenant_buildway_demo", "team_alpha", "agt_001", log_date, 20, 10, 3, 2, 1, "latest")
    repo.add_review(review_daily_performance(latest))
    repo.add_closing_score(calculate_hidden_closing_score(latest))

    reviews = repo.list_reviews("tenant_buildway_demo", agent_id="agt_001")
    scores = repo.list_closing_scores("tenant_buildway_demo", agent_id="agt_001")
    dashboard = DashboardService(repo).manager_dashboard("tenant_buildway_demo", "mgr_001", UserRole.MANAGER)

    assert len(reviews) == 1
    assert len(scores) == 1
    assert scores[0].hidden_score > 0
    assert len([log for log in dashboard["daily_logs"] if log.agent_id == "agt_001" and log.activity_date == log_date]) == 1


def test_sqlite_password_login_for_default_roles(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "group_training.sqlite3")
    auth = AuthService(repo)

    assert auth.authenticate("tenant_buildway_demo", "admin@buildway.demo", "Admin123!").role == UserRole.ADMIN
    assert auth.authenticate("tenant_buildway_demo", "manager@buildway.demo", "Manager123!").role == UserRole.MANAGER
    assert auth.authenticate("tenant_buildway_demo", "agent@buildway.demo", "Agent123!").role == UserRole.AGENT
    assert auth.authenticate("tenant_buildway_demo", "agent@buildway.demo", "wrong") is None
