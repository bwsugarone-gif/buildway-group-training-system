"""OCR extraction and rule-based parsing for the Streamlit group training app."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


SUPPORTED_OCR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".pdf"}
UNSUPPORTED_UPLOAD_EXTENSIONS = {".csv", ".xlsx"}
OCR_PREPROCESSING_MODES = {"original", "enhanced", "high_contrast"}
OCR_UNAVAILABLE_ERROR = "OCR 引擎未啟用，請確認 Tesseract 已安裝，或切換至 mock 測試模式。"


@dataclass
class OCRUploadResult:
    provider: str
    status: str
    text: str
    error: str | None = None
    is_mock: bool = False
    preprocessing_mode: str = "original"


CUSTOMER_FIELDS = {
    "name": "",
    "phone": "",
    "email": "",
    "stage": "",
    "source": "",
    "notes": "",
    "next_action": "",
    "next_follow_up_date": "",
}

DAILY_LOG_FIELDS = {
    "customer_name": "",
    "activity_type": "",
    "activity_date": "",
    "call_count": 0,
    "whatsapp_count": 0,
    "appointment_count": 0,
    "meeting_count": 0,
    "closed_count": 0,
    "notes": "",
}

FOLLOW_UP_FIELDS = {
    "customer_name": "",
    "notes": "",
    "next_action": "",
    "next_follow_up_date": "",
}


FIELD_ALIASES = {
    "name": {"name", "customer", "customer name", "姓名", "客戶", "客戶姓名", "名稱"},
    "phone": {"phone", "tel", "telephone", "mobile", "電話", "手機", "聯絡電話"},
    "email": {"email", "e-mail", "電郵", "電子郵件", "郵箱"},
    "stage": {"stage", "status", "customer status", "客戶狀態", "階段", "狀態"},
    "source": {"source", "來源"},
    "notes": {"notes", "note", "remarks", "備註", "筆記"},
    "next_action": {"next action", "action", "下一步", "下步行動", "跟進行動"},
    "next_follow_up_date": {
        "next follow up",
        "next follow-up",
        "next follow up date",
        "next follow-up date",
        "follow up date",
        "date",
        "下次跟進",
        "下次跟進日期",
        "跟進日期",
        "日期",
    },
    "customer_name": {"customer", "customer name", "name", "客戶", "客戶姓名", "姓名", "名稱"},
    "activity_type": {"activity", "activity type", "工作類型", "活動類型"},
    "activity_date": {"date", "activity date", "日期", "工作日期", "活動日期"},
}

STAGE_ALIASES = {
    "cold": "Cold",
    "冷": "Cold",
    "冷淡": "Cold",
    "warm": "Warm",
    "暖": "Warm",
    "溫": "Warm",
    "hot": "Hot",
    "熱": "Hot",
    "熱門": "Hot",
    "proposal": "Proposal",
    "closing": "Proposal",
    "建議書": "Proposal",
    "方案": "Proposal",
    "closed": "Closed",
    "成交": "Closed",
    "已成交": "Closed",
    "lost": "Lost",
    "流失": "Lost",
    "失去": "Lost",
}


def extract_text_from_upload(
    file_bytes: bytes,
    filename: str,
    provider: str = "auto",
    preprocessing_mode: str = "original",
) -> OCRUploadResult:
    """Extract OCR text from uploaded bytes using an explicit or configured provider."""
    requested_provider = (provider or os.environ.get("OCR_PROVIDER") or "auto").strip().lower()
    if requested_provider == "auto":
        requested_provider = (os.environ.get("OCR_PROVIDER") or "auto").strip().lower()
    normalized_preprocessing = _normalize_preprocessing_mode(preprocessing_mode)

    if requested_provider == "mock":
        return _mock_ocr_result()

    suffix = Path(filename or "").suffix.lower()
    if not file_bytes:
        return OCRUploadResult(
            provider="unavailable",
            status="empty",
            text="",
            error="empty_upload",
            preprocessing_mode=normalized_preprocessing,
        )
    if suffix in UNSUPPORTED_UPLOAD_EXTENSIONS or suffix not in SUPPORTED_OCR_EXTENSIONS:
        return OCRUploadResult(
            provider="unsupported",
            status="unsupported",
            text="",
            error=f"Unsupported file type: {suffix or 'unknown'}",
            preprocessing_mode=normalized_preprocessing,
        )
    if requested_provider not in {"auto", "tesseract"}:
        return OCRUploadResult(
            provider="unsupported",
            status="unsupported",
            text="",
            error=f"Unsupported OCR provider: {requested_provider}",
            preprocessing_mode=normalized_preprocessing,
        )

    return _extract_with_tesseract(file_bytes, suffix, normalized_preprocessing)


def extract_text_from_image(image_bytes: bytes) -> dict[str, Any]:
    """Backward-compatible wrapper; real OCR is used unless OCR_PROVIDER=mock."""
    result = extract_text_from_upload(image_bytes, "upload.png")
    return {
        "ok": result.status not in {"failed", "unavailable", "unsupported"},
        "raw_text": result.text,
        "error": result.error,
        "provider": result.provider,
        "status": result.status,
    }


def parse_customer_from_ocr_text(text: str) -> dict[str, Any]:
    """Parse customer fields from OCR text."""
    return convert_ocr_text_to_structured_data(text, "customer")


def get_ocr_provider_label(provider: str, status: str | None = None) -> str:
    """Return a stable display label for OCR provider/status."""
    normalized_provider = (provider or "unavailable").strip().lower()
    normalized_status = (status or "").strip().lower()
    if normalized_provider == "mock":
        return "mock"
    if normalized_provider == "tesseract":
        return "tesseract"
    if normalized_provider == "unsupported" or normalized_status == "unsupported":
        return "unsupported"
    if normalized_provider == "unavailable" or normalized_status == "unavailable":
        return "unavailable"
    return normalized_provider or "unavailable"


def _normalize_preprocessing_mode(mode: str) -> str:
    normalized = (mode or "original").strip().lower()
    return normalized if normalized in OCR_PREPROCESSING_MODES else "original"


def _extract_with_tesseract(file_bytes: bytes, suffix: str, preprocessing_mode: str) -> OCRUploadResult:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = Path(temp_file.name)

        extraction = _extract_text_with_core_ocr(temp_path, preprocessing_mode=preprocessing_mode)
        status = str(extraction.get("ocr_status") or "failed").lower()
        text = str(extraction.get("extracted_text") or "")
        warning = str(extraction.get("warning") or "")
        message = str(extraction.get("ocr_message") or "")
        result_preprocessing = str(extraction.get("preprocessing_mode") or preprocessing_mode)

        if status in {"success", "skipped_selectable"}:
            return OCRUploadResult(provider="tesseract", status="success", text=text, error=None, preprocessing_mode=result_preprocessing)
        if status == "empty":
            return OCRUploadResult(provider="tesseract", status="empty", text="", error=message or None, preprocessing_mode=result_preprocessing)
        if status == "unavailable":
            error = f"{OCR_UNAVAILABLE_ERROR} {warning}".strip() if warning else OCR_UNAVAILABLE_ERROR
            return OCRUploadResult(provider="unavailable", status="unavailable", text=text, error=error, preprocessing_mode=result_preprocessing)
        if status == "unsupported":
            return OCRUploadResult(provider="unsupported", status="unsupported", text=text, error=message or warning or None, preprocessing_mode=result_preprocessing)
        return OCRUploadResult(
            provider="tesseract",
            status="failed",
            text=text,
            error=warning or message or "OCR failed",
            preprocessing_mode=result_preprocessing,
        )
    except Exception as exc:
        return OCRUploadResult(provider="tesseract", status="failed", text="", error=str(exc), preprocessing_mode=preprocessing_mode)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _extract_text_with_core_ocr(file_path: Path, preprocessing_mode: str = "original") -> dict[str, Any]:
    """Lazy-load the core OCR engine so missing OCR deps cannot crash app startup."""
    try:
        from core.ocr.ocr_engine import extract_text_with_ocr
    except Exception as exc:
        return {
            "ocr_status": "UNAVAILABLE",
            "extracted_text": "",
            "warning": str(exc),
            "ocr_message": OCR_UNAVAILABLE_ERROR,
            "preprocessing_mode": preprocessing_mode,
        }
    try:
        return extract_text_with_ocr(file_path, preprocessing_mode=preprocessing_mode)
    except Exception as exc:
        return {
            "ocr_status": "FAILED",
            "extracted_text": "",
            "warning": str(exc),
            "ocr_message": "OCR extraction failed.",
            "preprocessing_mode": preprocessing_mode,
        }


def _mock_ocr_result() -> OCRUploadResult:
    return OCRUploadResult(
        provider="mock",
        status="success",
        text=(
            "Name: Demo Customer\n"
            "Phone: 91234567\n"
            "Email: demo.customer@example.com\n"
            "Stage: Warm\n"
            "Source: OCR Upload\n"
            "Date: {today}\n"
            "Calls: 3\n"
            "WhatsApp: 2\n"
            "Appointments: 1\n"
            "Meetings: 0\n"
            "Closed: 0\n"
            "Notes: Extracted by mock OCR. Please review before saving.\n"
            "Next Action: Follow up by phone\n"
            "Next Follow Up: {today}"
        ).format(today=date.today().isoformat()),
        error=None,
        is_mock=True,
    )


def convert_ocr_text_to_structured_data(raw_text: str, data_type: str = "customer") -> dict[str, Any]:
    """Convert raw OCR text into structured CRM, activity, or follow-up fields."""
    normalized_type = data_type.strip().lower()
    parsed = _parse_key_values(raw_text)
    if normalized_type == "daily_log":
        return _convert_daily_log(raw_text, parsed)
    if normalized_type == "follow_up_note":
        return _convert_follow_up(raw_text, parsed)
    return _convert_customer(raw_text, parsed)


def _parse_key_values(raw_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in raw_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
        elif "：" in line:
            key, value = line.split("：", 1)
        else:
            continue
        canonical = _canonical_field(key)
        if canonical and value.strip():
            values[canonical] = value.strip()
    return values


def _canonical_field(label: str) -> str:
    normalized = label.strip().lower()
    for field, aliases in FIELD_ALIASES.items():
        if normalized in {alias.lower() for alias in aliases}:
            return field
    return ""


def _convert_customer(raw_text: str, parsed: dict[str, str]) -> dict[str, Any]:
    result = dict(CUSTOMER_FIELDS)
    result.update({key: parsed.get(key, result[key]) for key in result})
    result["phone"] = result["phone"] or _first_match(raw_text, r"(\+?\d[\d\s-]{6,}\d)")
    result["email"] = result["email"] or _first_match(raw_text, r"[\w.\-+]+@[\w.\-]+\.\w+")
    result["stage"] = _normalize_stage(result["stage"]) or _stage_from_text(raw_text)
    result["next_follow_up_date"] = _normalize_date(result["next_follow_up_date"] or _date_from_text(raw_text))
    if not result["name"] and raw_text.strip():
        result["name"] = _first_non_empty_line(raw_text)
    return result


def _convert_daily_log(raw_text: str, parsed: dict[str, str]) -> dict[str, Any]:
    result = dict(DAILY_LOG_FIELDS)
    result.update({key: parsed.get(key, result[key]) for key in result})
    result["customer_name"] = result["customer_name"] or parsed.get("name", "")
    result["activity_type"] = result["activity_type"] or ("OCR" if raw_text.strip() else "")
    result["activity_date"] = _normalize_date(result["activity_date"] or _date_from_text(raw_text))
    result["call_count"] = _count_from_text(raw_text, ["calls", "call", "電話", "通話"], result["call_count"])
    result["whatsapp_count"] = _count_from_text(raw_text, ["whatsapp", "whatsapps"], result["whatsapp_count"])
    result["appointment_count"] = _count_from_text(raw_text, ["appointments", "appointment", "預約", "約見"], result["appointment_count"])
    result["meeting_count"] = _count_from_text(raw_text, ["meetings", "meeting", "會議", "面談"], result["meeting_count"])
    result["closed_count"] = _count_from_text(raw_text, ["closed", "closings", "closing", "成交"], result["closed_count"])
    return result


def _convert_follow_up(raw_text: str, parsed: dict[str, str]) -> dict[str, Any]:
    result = dict(FOLLOW_UP_FIELDS)
    result.update({key: parsed.get(key, result[key]) for key in result})
    result["customer_name"] = result["customer_name"] or parsed.get("name", "")
    result["next_follow_up_date"] = _normalize_date(result["next_follow_up_date"] or _date_from_text(raw_text))
    if not result["notes"] and raw_text.strip():
        result["notes"] = parsed.get("source", "") or _first_non_empty_line(raw_text)
    return result


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(0).strip() if match else ""


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return re.split(r"[:：]", cleaned, maxsplit=1)[-1].strip()
    return ""


def _normalize_stage(value: str) -> str:
    normalized = value.strip().lower()
    return STAGE_ALIASES.get(normalized, "")


def _stage_from_text(text: str) -> str:
    lowered = text.lower()
    for alias, stage in STAGE_ALIASES.items():
        if alias in lowered:
            return stage
    return ""


def _date_from_text(text: str) -> str:
    return _first_match(text, r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")


def _normalize_date(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", value)
    if not match:
        return ""
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _count_from_text(text: str, labels: list[str], default: int | str) -> int:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:：]?\s*(\d+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    try:
        return int(default)
    except (TypeError, ValueError):
        return 0
