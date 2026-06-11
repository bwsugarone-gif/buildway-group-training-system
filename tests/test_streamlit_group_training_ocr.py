import json
import inspect
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from apps.streamlit_group_training.services import ocr_service
from apps.streamlit_group_training.services.ocr_service import (
    OCRUploadResult,
    convert_ocr_text_to_structured_data,
    extract_text_from_upload,
    get_ocr_provider_label,
    parse_customer_from_ocr_text,
)
from core.ocr.ocr_engine import extract_text_with_ocr, preprocess_image
from verticals.group_training.models import Customer, CustomerStage, Team, User, UserRole
from verticals.group_training.services.customer_service import CustomerService
from verticals.group_training.services.repository import GroupTrainingRepository


I18N_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit_group_training" / "i18n"


def _sample_image() -> Image.Image:
    image = Image.new("RGB", (12, 8), "white")
    for x in range(image.width):
        for y in range(image.height):
            value = 40 if (x + y) % 2 else 220
            image.putpixel((x, y), (value, value, value))
    return image


def _image_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_ocr_service_exports_import_compatibility_names():
    assert OCRUploadResult
    assert callable(extract_text_from_upload)
    assert callable(parse_customer_from_ocr_text)
    assert callable(get_ocr_provider_label)
    assert callable(convert_ocr_text_to_structured_data)


def test_core_ocr_signature_accepts_preprocessing_mode():
    signature = inspect.signature(extract_text_with_ocr)

    assert "preprocessing_mode" in signature.parameters
    assert signature.parameters["preprocessing_mode"].default == "original"


def test_preprocessing_helper_returns_image():
    processed = preprocess_image(_sample_image(), "enhanced")

    assert isinstance(processed, Image.Image)


def test_original_preprocessing_mode_no_processing():
    image = _sample_image()
    processed = preprocess_image(image, "original")

    assert processed is image
    assert processed.size == image.size


def test_enhanced_preprocessing_mode_increases_size():
    image = _sample_image()
    processed = preprocess_image(image, "enhanced")

    assert processed.size[0] == image.size[0] * 2
    assert processed.size[1] == image.size[1] * 2
    assert processed.mode == "L"


def test_high_contrast_preprocessing_mode_returns_binary_like_image():
    image = _sample_image()
    processed = preprocess_image(image, "high_contrast")
    non_empty_bins = {idx for idx, count in enumerate(processed.histogram()) if count}

    assert processed.size[0] == image.size[0] * 3
    assert processed.size[1] == image.size[1] * 3
    assert processed.mode == "L"
    assert non_empty_bins.issubset({0, 255})


def test_mock_provider_explicitly_returns_mock_result():
    result = extract_text_from_upload(b"fake-image", "upload.png", provider="mock")

    assert result.provider == "mock"
    assert result.status == "success"
    assert result.is_mock is True
    assert result.cost_mode == "test"
    assert "Demo Customer" in result.text


def test_auto_provider_does_not_return_mock_by_default(monkeypatch):
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Ada Chan\nPhone: 91234567",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "upload.png", provider="auto")

    assert result.provider == "tesseract"
    assert result.status == "success"
    assert result.is_mock is False
    assert result.cost_mode == "free"
    assert "Demo Customer" not in result.text


def test_default_provider_uses_tesseract_when_env_missing(monkeypatch):
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Default Tesseract Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "upload.png")

    assert result.provider == "tesseract"
    assert result.status == "success"
    assert result.text == "Name: Default Tesseract Customer"


def test_env_provider_can_enable_mock_explicitly(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "mock")

    result = extract_text_from_upload(b"fake-image", "upload.png")

    assert result.provider == "mock"
    assert result.is_mock is True
    assert "Demo Customer" in result.text


def test_auto_provider_with_gemini_key_still_uses_tesseract(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    called = {"tesseract": False, "gemini": False}

    def fake_tesseract(path, preprocessing_mode="original"):
        called["tesseract"] = True
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Free OCR Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }

    def fake_gemini(file_bytes, mime_type, api_key):
        called["gemini"] = True
        return "Name: Gemini Customer"

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_tesseract)
    monkeypatch.setattr(ocr_service, "_call_gemini_vision_ocr", fake_gemini)

    result = extract_text_from_upload(b"fake-image", "upload.png", provider="auto")

    assert result.provider == "tesseract"
    assert result.text == "Name: Free OCR Customer"
    assert called == {"tesseract": True, "gemini": False}


def test_upload_flow_passes_preprocessing_mode(monkeypatch):
    captured = {}

    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        captured["preprocessing_mode"] = preprocessing_mode
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Enhanced Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(
        _image_bytes(_sample_image()),
        "upload.png",
        provider="auto",
        preprocessing_mode="enhanced",
    )

    assert captured["preprocessing_mode"] == "enhanced"
    assert result.preprocessing_mode == "enhanced"
    assert result.text == "Name: Enhanced Customer"


def test_mock_mode_not_affected_by_preprocessing_mode():
    result = extract_text_from_upload(
        b"fake-image",
        "upload.png",
        provider="mock",
        preprocessing_mode="high_contrast",
    )

    assert result.provider == "mock"
    assert result.preprocessing_mode == "original"
    assert "Demo Customer" in result.text


@pytest.mark.parametrize(
    ("filename", "expected_mime"),
    [
        ("sample.jpg", "image/jpeg"),
        ("sample.png", "image/png"),
        ("sample.pdf", "application/pdf"),
    ],
)
def test_gemini_provider_explicitly_runs_vision_ocr(monkeypatch, tmp_path, filename, expected_mime):
    captured = {}
    monkeypatch.setenv("ENABLE_PAID_OCR", "true")
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(tmp_path / "ocr_usage.jsonl"))

    def fake_call(file_bytes, mime_type, api_key):
        captured["file_bytes"] = file_bytes
        captured["mime_type"] = mime_type
        captured["api_key"] = api_key
        return "Name: Gemini OCR Customer\nPhone: 91234567"

    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "fake-gemini-key")
    monkeypatch.setattr(ocr_service, "_call_gemini_vision_ocr", fake_call)

    result = extract_text_from_upload(b"fake-content", filename, provider="gemini", preprocessing_mode="high_contrast")

    assert result.provider == "gemini"
    assert result.status == "success"
    assert result.cost_mode == "paid"
    assert result.preprocessing_mode == "original"
    assert result.text.startswith("Name: Gemini OCR Customer")
    assert captured == {
        "file_bytes": b"fake-content",
        "mime_type": expected_mime,
        "api_key": "fake-gemini-key",
    }


def test_gemini_provider_missing_api_key_returns_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_PAID_OCR", "true")
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(tmp_path / "ocr_usage.jsonl"))
    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "")

    result = extract_text_from_upload(b"fake-content", "sample.png", provider="gemini")

    assert result.provider == "gemini"
    assert result.status == "unavailable"
    assert result.cost_mode == "paid"
    assert "GEMINI_API_KEY" in (result.error or "")
    assert "Demo Customer" not in result.text


def test_gemini_provider_disabled_when_paid_ocr_not_enabled(monkeypatch, tmp_path):
    monkeypatch.delenv("ENABLE_PAID_OCR", raising=False)
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(tmp_path / "ocr_usage.jsonl"))
    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "fake-key")

    result = extract_text_from_upload(b"fake-content", "sample.png", provider="gemini")

    assert result.provider == "gemini"
    assert result.status == "unavailable"
    assert result.cost_mode == "paid"
    assert "ENABLE_PAID_OCR" in (result.error or "")
    assert "Demo Customer" not in result.text


def test_gemini_provider_allowed_for_admin_role_when_env_disabled(monkeypatch, tmp_path):
    captured = {"called": False}
    monkeypatch.delenv("ENABLE_PAID_OCR", raising=False)
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(tmp_path / "ocr_usage.jsonl"))
    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "fake-key")

    def fake_call(file_bytes, mime_type, api_key):
        captured["called"] = True
        return "Name: Admin Gemini Customer"

    monkeypatch.setattr(ocr_service, "_call_gemini_vision_ocr", fake_call)

    result = extract_text_from_upload(
        b"fake-content",
        "sample.png",
        provider="gemini",
        actor_id="admin_001",
        tenant_id="tenant_buildway_demo",
        paid_ocr_allowed_by_role=True,
    )

    assert result.provider == "gemini"
    assert result.status == "success"
    assert captured["called"] is True


def test_gemini_provider_daily_quota_blocks_api_call(monkeypatch, tmp_path):
    usage_log = tmp_path / "ocr_usage.jsonl"
    monkeypatch.setenv("ENABLE_PAID_OCR", "true")
    monkeypatch.setenv("MAX_PAID_OCR_PER_DAY", "1")
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(usage_log))
    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "fake-key")
    today = ocr_service.date.today().isoformat()
    usage_log.write_text(
        json.dumps({"date": today, "provider": "gemini", "counted": True}) + "\n",
        encoding="utf-8",
    )

    def fake_call(file_bytes, mime_type, api_key):
        raise AssertionError("Gemini API should not be called after quota is exhausted")

    monkeypatch.setattr(ocr_service, "_call_gemini_vision_ocr", fake_call)

    result = extract_text_from_upload(b"fake-content", "sample.png", provider="gemini")

    assert result.provider == "gemini"
    assert result.status == "unavailable"
    assert result.error == "今日高準確識別額度已用完，請稍後再試或聯絡管理員"


def test_gemini_provider_logs_paid_usage(monkeypatch, tmp_path):
    usage_log = tmp_path / "ocr_usage.jsonl"
    monkeypatch.setenv("ENABLE_PAID_OCR", "true")
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(usage_log))
    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "fake-key")
    monkeypatch.setattr(ocr_service, "_call_gemini_vision_ocr", lambda file_bytes, mime_type, api_key: "Name: Logged Customer")

    result = extract_text_from_upload(
        b"fake-content",
        "sample.png",
        provider="gemini",
        actor_id="agt_001",
        tenant_id="tenant_buildway_demo",
    )
    events = [json.loads(line) for line in usage_log.read_text(encoding="utf-8").splitlines()]

    assert result.status == "success"
    assert any(event["event"] == "api_call" and event["counted"] is True for event in events)
    assert any(event["event"] == "success" and event["actor_id"] == "agt_001" for event in events)


def test_gemini_provider_unsupported_file_type_does_not_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_PAID_OCR", "true")
    monkeypatch.setenv("OCR_USAGE_LOG_PATH", str(tmp_path / "ocr_usage.jsonl"))
    monkeypatch.setattr(ocr_service, "_get_gemini_api_key", lambda: "fake-key")

    result = extract_text_from_upload(b"fake-content", "sample.webp", provider="gemini")

    assert result.provider == "gemini"
    assert result.status == "unsupported"
    assert result.cost_mode == "paid"
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


def test_deepseek_structured_extraction_overlays_rule_based_parser(monkeypatch):
    monkeypatch.setattr(
        ocr_service,
        "_call_deepseek_for_ocr",
        lambda prompt: '{"name":"DeepSeek Customer","phone":"98765432","email":"deepseek@example.com","stage":"Hot","next_follow_up_date":"2026-07-08"}',
    )

    structured = convert_ocr_text_to_structured_data("Name: Rule Customer\nPhone: 91234567", "customer")

    assert structured["name"] == "DeepSeek Customer"
    assert structured["phone"] == "98765432"
    assert structured["email"] == "deepseek@example.com"
    assert structured["stage"] == "Hot"
    assert structured["next_follow_up_date"] == "2026-07-08"


def test_invalid_deepseek_structured_extraction_keeps_rule_based_parser(monkeypatch):
    monkeypatch.setattr(ocr_service, "_call_deepseek_for_ocr", lambda prompt: "not json")

    structured = convert_ocr_text_to_structured_data("Name: Rule Customer\nPhone: 91234567", "customer")

    assert structured["name"] == "Rule Customer"
    assert structured["phone"] == "91234567"


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

    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        captured["path"] = Path(path)
        captured["preprocessing_mode"] = preprocessing_mode
        assert captured["path"].exists()
        assert captured["path"].suffix == ".png"
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: OCR Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "receipt.png", provider="tesseract")

    assert result.provider == "tesseract"
    assert result.status == "success"
    assert result.text == "Name: OCR Customer"
    assert captured["path"].exists() is False
    assert captured["preprocessing_mode"] == "original"


def test_gemini_api_key_does_not_change_provider_to_gemini_placeholder(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Real OCR Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)

    result = extract_text_from_upload(b"fake-image", "upload.png", provider="auto")

    assert result.provider == "tesseract"
    assert result.provider != "gemini-placeholder"
    assert result.cost_mode == "free"
    assert "Demo Customer" not in result.text


def test_tesseract_unavailable_does_not_crash_or_fallback_to_mock(monkeypatch):
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    def fake_unavailable(path, preprocessing_mode="original"):
        return {
            "ocr_status": "UNAVAILABLE",
            "extracted_text": "",
            "warning": "tesseract is not installed",
            "ocr_message": "OCR is unavailable.",
            "preprocessing_mode": preprocessing_mode,
        }

    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_unavailable)

    result = extract_text_from_upload(b"fake-image", "upload.png", provider="auto")

    assert result.provider == "unavailable"
    assert result.status == "unavailable"
    assert result.is_mock is False
    assert "Tesseract" in (result.error or "")
    assert "Demo Customer" not in result.text


def test_legacy_core_ocr_signature_mismatch_does_not_crash(monkeypatch):
    def fake_import(name, *args, **kwargs):
        if name == "core.ocr.ocr_engine":
            def legacy_extract_text_with_ocr(path):
                return {
                    "ocr_status": "SUCCESS",
                    "extracted_text": "Name: Legacy OCR Customer",
                    "warning": "",
                    "ocr_message": "OCR extraction successful",
                }

            class LegacyModule:
                extract_text_with_ocr = staticmethod(legacy_extract_text_with_ocr)

            return LegacyModule
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)

    result = ocr_service._extract_text_with_core_ocr(Path("sample.png"), preprocessing_mode="enhanced")

    assert result["ocr_status"] == "SUCCESS"
    assert result["extracted_text"] == "Name: Legacy OCR Customer"
    assert result["preprocessing_mode"] == "enhanced"
    assert "legacy OCR path" in result["warning"]


def test_ocr_i18n_keys_match_between_locales():
    zh = json.loads((I18N_DIR / "zh_HK.json").read_text(encoding="utf-8"))
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))
    ocr_keys = {key for key in zh if key.startswith("ocr.") or key == "nav.ocr_data_capture"}

    assert set(zh) == set(en)
    assert "ocr.title" in ocr_keys
    assert "ocr.confirm_save" in ocr_keys
    assert "ocr.status" in ocr_keys
    assert "ocr.mode" in ocr_keys
    assert "ocr.cost_mode" in ocr_keys
    assert "ocr.preprocessing_mode" in ocr_keys


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
