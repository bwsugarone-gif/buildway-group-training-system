from datetime import date
from io import StringIO
from pathlib import Path

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
from apps.streamlit_group_training.i18n.loader import translate
from verticals.group_training.models import Customer, CustomerStage, User, UserRole
from verticals.group_training.services.auth_service import verify_password
from verticals.group_training.services.customer_service import CustomerService
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

    assert "SQLite" not in visible_text
    assert "group_training.sqlite3" not in visible_text
    assert "Phase" not in visible_text
    assert "MVP" not in visible_text


def test_customer_crm_does_not_show_import_or_export_controls():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=10)
    at.text_input[0].set_value("admin@buildway.demo")
    at.text_input[1].set_value("Admin123!")
    at.button[0].click()
    at.run(timeout=10)

    labels = [button.label for button in at.button] + [expander.label for expander in at.expander]
    assert translate("zh_HK", "customer.export_csv") not in labels
    assert translate("zh_HK", "customer.import_csv") not in labels


def test_group_training_app_no_long_tables_use_streamlit_dataframe_toolbar():
    source = Path(APP_PATH).read_text(encoding="utf-8")

    assert "st.dataframe" not in source
    assert ".dataframe(" not in source


def test_normalize_customer_import_dataframe_supports_english_headers():
    normalized = normalize_customer_import_dataframe(
        pd.DataFrame([{"name": "Ada", "phone": "", "stage": "Proposal", "next_meeting_date": "", "notes": "Demo"}])
    )

    assert normalized.iloc[0]["name"] == "Ada"
    assert normalized.iloc[0]["stage"] == "Proposal"
    assert normalized.iloc[0]["next_meeting_date"] == date.today()


def test_upload_download_data_page_has_three_sections_and_upload_controls():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=10)
    at.text_input[0].set_value("admin@buildway.demo")
    at.text_input[1].set_value("Admin123!")
    at.button[0].click()
    at.run(timeout=10)

    at.radio[0].set_value(translate("zh_HK", "nav.ocr_data_capture"))
    at.run(timeout=10)

    subheaders = [element.value for element in at.subheader]
    captions = [element.value for element in at.caption]
    assert translate("zh_HK", "ocr.title") in subheaders
    assert translate("zh_HK", "data.import_section") in subheaders
    assert translate("zh_HK", "data.export_section") in subheaders
    assert translate("zh_HK", "data.document_section") in subheaders
    assert translate("zh_HK", "data.import_description") in captions
    assert translate("zh_HK", "data.export_description") in captions
    assert translate("zh_HK", "data.document_description") in captions
    assert any(uploader.label == translate("zh_HK", "ocr.upload_image") for uploader in at.file_uploader)
    assert any(selectbox.label == translate("zh_HK", "ocr.data_type") for selectbox in at.selectbox)


def test_followup_visible_in_recent_records_for_agent_and_manager(tmp_path):
    repo = SQLiteGroupTrainingRepository(tmp_path / "followups.sqlite3")
    customer_service = CustomerService(repo)
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
