import json
from pathlib import Path

import pytest

from apps.streamlit_group_training.services.ocr_service import (
    convert_ocr_text_to_structured_data,
    extract_text_from_image,
)
from verticals.group_training.models import Customer, CustomerStage, Team, User, UserRole
from verticals.group_training.services.customer_service import CustomerService
from verticals.group_training.services.repository import GroupTrainingRepository


I18N_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit_group_training" / "i18n"


def test_ocr_service_without_api_key_does_not_crash(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = extract_text_from_image(b"fake-image")

    assert result["ok"] is True
    assert result["provider"] == "mock"
    assert "Demo Customer" in result["raw_text"]


def test_convert_customer_raw_text_outputs_basic_fields():
    structured = convert_ocr_text_to_structured_data(
        "Name: Ada Chan\nPhone: 91234567\nEmail: ada@example.com\nStage: Hot\nNext Follow Up: 2026-06-06",
        "customer",
    )

    assert structured["name"] == "Ada Chan"
    assert structured["phone"] == "91234567"
    assert structured["email"] == "ada@example.com"
    assert structured["stage"] == "Hot"
    assert structured["next_follow_up_date"] == "2026-06-06"


def test_convert_daily_log_raw_text_outputs_basic_fields():
    structured = convert_ocr_text_to_structured_data(
        "Customer: Ada Chan\nDate: 2026-06-06\nCalls: 5\nWhatsApp: 3\nAppointments: 2\nMeetings: 1\nClosed: 1",
        "daily_log",
    )

    assert structured["customer_name"] == "Ada Chan"
    assert structured["activity_date"] == "2026-06-06"
    assert structured["call_count"] == 5
    assert structured["whatsapp_count"] == 3
    assert structured["appointment_count"] == 2
    assert structured["meeting_count"] == 1
    assert structured["closed_count"] == 1


def test_ocr_i18n_keys_match_between_locales():
    zh = json.loads((I18N_DIR / "zh_HK.json").read_text(encoding="utf-8"))
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))
    ocr_keys = {key for key in zh if key.startswith("ocr.") or key == "nav.ocr_data_capture"}

    assert set(zh) == set(en)
    assert "ocr.title" in ocr_keys
    assert "ocr.confirm_save" in ocr_keys


def test_ocr_follow_up_save_cannot_cross_tenant():
    repo = GroupTrainingRepository()
    service = CustomerService(repo)
    repo.add_team(Team("tenant_a", "team_a", "Team A", "mgr_a"))
    repo.add_team(Team("tenant_b", "team_b", "Team B", "mgr_b"))
    repo.add_user(User("tenant_a", "agt_a", "Agent A", "a@example.com", UserRole.AGENT, "team_a"))
    repo.add_user(User("tenant_b", "agt_b", "Agent B", "b@example.com", UserRole.AGENT, "team_b"))
    other_tenant_customer = repo.add_customer(
        Customer("tenant_b", "team_b", "agt_b", "Other Tenant Customer", CustomerStage.WARM)
    )

    with pytest.raises(ValueError, match="customer not found"):
        service.add_followup("tenant_a", other_tenant_customer.id, "agt_a", "OCR note", "Call tomorrow")
