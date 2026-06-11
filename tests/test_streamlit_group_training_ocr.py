import json
from pathlib import Path

import pytest

from apps.streamlit_group_training.services import ocr_service
from apps.streamlit_group_training.services.ocr_service import (
    convert_ocr_text_to_structured_data,
    extract_text_from_upload,
)
from verticals.group_training.models import Customer, CustomerStage, Team, User, UserRole
from verticals.group_training.services.customer_service import CustomerService
from verticals.group_training.services.repository import GroupTrainingRepository


I18N_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit_group_training" / "i18n"


def test_mock_provider_explicitly_returns_mock_result():
    result = extract_text_from_upload(b"fake-image", "upload.png", provider="mock")

    assert result.provider == "mock"
    assert result.status == "success"
    assert result.is_mock is True
    assert "Demo Customer" in result.text


def test_auto_provider_does_not_return_mock_by_default(monkeypatch):
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    def fake_extract_text_with_ocr(path):
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Ada Chan\nPhone: 91234567",
            "warning": "",
            "ocr_message": "OCR extraction successful",
        }

    monkeypatch.setattr(ocr_service, "extract_text_with_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "upload.png", provider="auto")

    assert result.provider == "tesseract"
    assert result.status == "success"
    assert result.is_mock is False
    assert "Demo Customer" not in result.text


@pytest.mark.parametrize("filename", ["customers.csv", "customers.xlsx"])
def test_unsupported_csv_xlsx_does_not_return_demo_customer(filename):
    result = extract_text_from_upload(b"name,phone", filename, provider="auto")

    assert result.provider == "unsupported"
    assert result.status == "unsupported"
    assert "Demo Customer" not in result.text


def test_empty_ocr_result_does_not_create_demo_customer():
    structured = convert_ocr_text_to_structured_data("", "customer")

    assert structured["name"] == ""
    assert structured["phone"] == ""
    assert structured["email"] == ""
    assert "Demo Customer" not in structured.values()


def test_parser_extracts_chinese_customer_fields():
    structured = convert_ocr_text_to_structured_data(
        "姓名：陳大文\n電話：91234567\n電郵：chan@example.com\n階段：熱\n下次跟進：2026-06-06",
        "customer",
    )

    assert structured["name"] == "陳大文"
    assert structured["phone"] == "91234567"
    assert structured["email"] == "chan@example.com"
    assert structured["stage"] == "Hot"
    assert structured["next_follow_up_date"] == "2026-06-06"


def test_parser_extracts_english_customer_fields():
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


def test_tesseract_adapter_can_be_mocked_without_real_tesseract(monkeypatch):
    captured = {}

    def fake_extract_text_with_ocr(path):
        captured["path"] = Path(path)
        assert captured["path"].exists()
        assert captured["path"].suffix == ".png"
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: OCR Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
        }

    monkeypatch.setattr(ocr_service, "extract_text_with_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "receipt.png", provider="tesseract")

    assert result.provider == "tesseract"
    assert result.status == "success"
    assert result.text == "Name: OCR Customer"
    assert captured["path"].exists() is False


def test_gemini_api_key_does_not_change_provider_to_gemini_placeholder(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    def fake_extract_text_with_ocr(path):
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Real OCR Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
        }

    monkeypatch.setattr(ocr_service, "extract_text_with_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "upload.png", provider="auto")

    assert result.provider == "tesseract"
    assert result.provider != "gemini-placeholder"
    assert "Demo Customer" not in result.text


def test_ocr_i18n_keys_match_between_locales():
    zh = json.loads((I18N_DIR / "zh_HK.json").read_text(encoding="utf-8"))
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))
    ocr_keys = {key for key in zh if key.startswith("ocr.") or key == "nav.ocr_data_capture"}

    assert set(zh) == set(en)
    assert "ocr.title" in ocr_keys
    assert "ocr.confirm_save" in ocr_keys
    assert "ocr.status" in ocr_keys


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
