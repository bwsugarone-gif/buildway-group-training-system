from datetime import date
from io import StringIO

import pandas as pd
from streamlit.testing.v1 import AppTest

from apps.streamlit_group_training.app import (
    TENANT_ID,
    import_customers_from_dataframe,
    normalize_customer_import_dataframe,
    request_password_reset,
    signup_user,
    visible_followups_to_dataframe,
)
from verticals.group_training.models import Customer, CustomerStage, User, UserRole
from verticals.group_training.services.auth_service import verify_password
from verticals.group_training.services.sqlite_repository import (
    DEFAULT_TEAM_ID,
    SQLiteGroupTrainingRepository,
)


APP_PATH = "apps/streamlit_group_training/app.py"


def test_signup_creates_user_with_hashed_password(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "signup.sqlite3")

    ok, message_key = signup_user(repo, "Demo Agent", "demo.agent@example.com", "Secret123!", "Secret123!", "Agent")
    user = repo.find_user_by_email(TENANT_ID, "demo.agent@example.com")

    assert ok is True
    assert message_key == "auth.signup_success"
    assert user is not None
    assert user.password_hash != "Secret123!"
    assert user.password_hash.startswith("pbkdf2_sha256$")
    assert verify_password("Secret123!", user.password_hash)
    assert user.tenant_id == TENANT_ID
    assert user.team_id == DEFAULT_TEAM_ID


def test_signup_duplicate_email_blocked(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "duplicate.sqlite3")

    first = signup_user(repo, "Demo Agent", "dup@example.com", "Secret123!", "Secret123!", "Agent")
    second = signup_user(repo, "Demo Agent 2", "dup@example.com", "Secret123!", "Secret123!", "Agent")

    assert first[0] is True
    assert second == (False, "auth.signup_email_exists")


def test_forgot_password_flow_does_not_crash_or_expose_account_status(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "reset.sqlite3")

    existing = request_password_reset(repo, "admin@buildway.demo")
    missing = request_password_reset(repo, "missing@example.com")

    assert existing == "auth.reset_request_created"
    assert missing == "auth.reset_request_created"


def test_csv_import_creates_customers(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "csv.sqlite3")
    user = repo.get_user(TENANT_ID, "mgr_001")
    dataframe = pd.read_csv(
        StringIO(
            "姓名,電話,客戶階段,下次會議日期,備註\n"
            "Ada,91234567,熱,2026-06-06,VIP\n"
            ",99999999,暖,2026-06-06,skip empty name\n"
            "Ben,,invalid,bad-date,No phone\n"
        )
    )

    imported = import_customers_from_dataframe(repo, user, dataframe, "agt_001")
    customers = repo.list_customers(TENANT_ID, agent_id="agt_001")

    assert imported == 2
    assert {customer.name for customer in customers} >= {"Ada", "Ben"}
    assert next(customer for customer in customers if customer.name == "Ada").stage == CustomerStage.HOT
    ben = next(customer for customer in customers if customer.name == "Ben")
    assert ben.stage == CustomerStage.COLD
    assert ben.next_meeting_date == date.today()


def test_csv_import_tenant_isolation(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "tenant.sqlite3")
    repo.add_user(User("tenant_other", "agt_other", "Other Agent", "other@example.com", UserRole.AGENT, "team_other"))
    repo.add_customer(Customer("tenant_other", "team_other", "agt_other", "Other Tenant Customer", CustomerStage.WARM))
    user = repo.get_user(TENANT_ID, "agt_001")
    dataframe = pd.DataFrame([{"name": "Tenant A Import", "stage": "Warm"}])

    import_customers_from_dataframe(repo, user, dataframe)

    assert [customer.name for customer in repo.list_customers("tenant_other")] == ["Other Tenant Customer"]
    assert any(customer.name == "Tenant A Import" for customer in repo.list_customers(TENANT_ID))


def test_agent_csv_import_ignores_other_agent_target(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "agent.sqlite3")
    user = repo.get_user(TENANT_ID, "agt_001")
    dataframe = pd.DataFrame([{"name": "Agent Import", "stage": "Warm"}])

    import_customers_from_dataframe(repo, user, dataframe, "agt_999")
    imported_customer = next(customer for customer in repo.list_customers(TENANT_ID) if customer.name == "Agent Import")

    assert imported_customer.agent_id == "agt_001"


def test_login_page_does_not_show_database_path():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=10)
    visible_text = "\n".join(str(element.value) for element in [*at.caption, *at.markdown, *at.subheader])

    assert "SQLite 資料庫" not in visible_text
    assert "SQLite database" not in visible_text
    assert "group_training.sqlite3" not in visible_text
    assert "Phase" not in visible_text
    assert "MVP" not in visible_text


def test_normalize_customer_import_dataframe_supports_english_headers():
    normalized = normalize_customer_import_dataframe(
        pd.DataFrame([{"name": "Ada", "phone": "", "stage": "Proposal", "next_meeting_date": "", "notes": "Demo"}])
    )

    assert normalized.iloc[0]["name"] == "Ada"
    assert normalized.iloc[0]["stage"] == "Proposal"
    assert normalized.iloc[0]["next_meeting_date"] == date.today()


def test_upload_data_page_ui_does_not_crash_after_login():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=10)
    at.text_input[0].set_value("admin@buildway.demo")
    at.text_input[1].set_value("Admin123!")
    at.button[0].click()
    at.run(timeout=10)

    at.radio[0].set_value("上載資料")
    at.run(timeout=10)

    assert at.subheader[0].value == "上載資料"
    assert at.file_uploader[0].label == "上載圖片或文件"
    assert any(selectbox.label == "資料類型" for selectbox in at.selectbox)


def test_followup_visible_in_recent_records_for_agent_and_manager(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "followups.sqlite3")
    customer_service = __import__(
        "verticals.group_training.services.customer_service",
        fromlist=["CustomerService"],
    ).CustomerService(repo)
    agent_customer = customer_service.create_customer(TENANT_ID, DEFAULT_TEAM_ID, "agt_001", "Agent Customer", "Warm")
    other_customer = customer_service.create_customer(TENANT_ID, DEFAULT_TEAM_ID, "agt_002", "Other Customer", "Warm")
    customer_service.add_followup(TENANT_ID, agent_customer.id, "agt_001", "Agent note", "Call tomorrow")
    customer_service.add_followup(TENANT_ID, other_customer.id, "agt_002", "Other note", "Send proposal")

    agent = repo.get_user(TENANT_ID, "agt_001")
    manager = repo.get_user(TENANT_ID, "mgr_001")
    agent_df = visible_followups_to_dataframe(repo, agent, "en")
    manager_df = visible_followups_to_dataframe(repo, manager, "en")

    assert set(agent_df["customer"]) == {"Agent Customer"}
    assert set(manager_df["customer"]) >= {"Agent Customer", "Other Customer"}
