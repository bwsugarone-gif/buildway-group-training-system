"""OCR extraction and rule-based parsing for the Streamlit group training MVP."""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Any


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
    "name": {"name", "customer", "customer name", "客戶", "客戶姓名", "姓名"},
    "phone": {"phone", "tel", "mobile", "電話", "手機"},
    "email": {"email", "e-mail", "電郵", "郵箱"},
    "stage": {"stage", "客戶階段", "階段"},
    "source": {"source", "來源"},
    "notes": {"notes", "note", "remarks", "備註", "跟進備註"},
    "next_action": {"next action", "action", "下一步", "後續行動"},
    "next_follow_up_date": {"next follow up", "follow up date", "next follow-up date", "下次跟進", "跟進日期"},
    "customer_name": {"customer", "customer name", "客戶", "客戶姓名"},
    "activity_type": {"activity", "activity type", "工作類型", "活動類型"},
    "activity_date": {"date", "activity date", "日期", "工作日期"},
}

STAGE_ALIASES = {
    "cold": "Cold",
    "冷": "Cold",
    "warm": "Warm",
    "暖": "Warm",
    "hot": "Hot",
    "熱": "Hot",
    "proposal": "Proposal",
    "方案": "Proposal",
    "closing": "Proposal",
    "closed": "Closed",
    "已成交": "Closed",
    "成交": "Closed",
    "lost": "Lost",
    "已流失": "Lost",
    "流失": "Lost",
}


def extract_text_from_image(image_bytes: bytes) -> dict[str, Any]:
    """
    Return OCR text using a safe MVP placeholder.

    A future Gemini Vision adapter can branch on GEMINI_API_KEY here. The current
    MVP never requires the key and never writes extracted data automatically.
    """
    if not image_bytes:
        return {"ok": False, "raw_text": "", "error": "empty_image", "provider": "mock"}

    provider = "gemini-placeholder" if os.environ.get("GEMINI_API_KEY") else "mock"
    return {
        "ok": True,
        "raw_text": (
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
        "error": None,
        "provider": provider,
    }


def convert_ocr_text_to_structured_data(raw_text: str, data_type: str) -> dict[str, Any]:
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
        if normalized in aliases:
            return field
    return ""


def _convert_customer(raw_text: str, parsed: dict[str, str]) -> dict[str, Any]:
    result = dict(CUSTOMER_FIELDS)
    result.update({key: parsed.get(key, result[key]) for key in result})
    result["phone"] = result["phone"] or _first_match(raw_text, r"(\+?\d[\d\s-]{6,}\d)")
    result["email"] = result["email"] or _first_match(raw_text, r"[\w.\-+]+@[\w.\-]+\.\w+")
    result["stage"] = _normalize_stage(result["stage"]) or _stage_from_text(raw_text)
    result["next_follow_up_date"] = _normalize_date(result["next_follow_up_date"] or _date_from_text(raw_text))
    if not result["name"]:
        result["name"] = _first_non_empty_line(raw_text)
    return result


def _convert_daily_log(raw_text: str, parsed: dict[str, str]) -> dict[str, Any]:
    result = dict(DAILY_LOG_FIELDS)
    result.update({key: parsed.get(key, result[key]) for key in result})
    result["customer_name"] = result["customer_name"] or parsed.get("name", "")
    result["activity_type"] = result["activity_type"] or "OCR"
    result["activity_date"] = _normalize_date(result["activity_date"] or _date_from_text(raw_text)) or date.today().isoformat()
    result["call_count"] = _count_from_text(raw_text, ["calls", "call", "電話", "通話"], result["call_count"])
    result["whatsapp_count"] = _count_from_text(raw_text, ["whatsapp", "whatsapps"], result["whatsapp_count"])
    result["appointment_count"] = _count_from_text(raw_text, ["appointments", "appointment", "約見", "預約"], result["appointment_count"])
    result["meeting_count"] = _count_from_text(raw_text, ["meetings", "meeting", "見客", "會議"], result["meeting_count"])
    result["closed_count"] = _count_from_text(raw_text, ["closed", "closings", "closing", "成交"], result["closed_count"])
    return result


def _convert_follow_up(raw_text: str, parsed: dict[str, str]) -> dict[str, Any]:
    result = dict(FOLLOW_UP_FIELDS)
    result.update({key: parsed.get(key, result[key]) for key in result})
    result["customer_name"] = result["customer_name"] or parsed.get("name", "")
    result["next_follow_up_date"] = _normalize_date(result["next_follow_up_date"] or _date_from_text(raw_text))
    if not result["notes"]:
        result["notes"] = parsed.get("source", "") or _first_non_empty_line(raw_text)
    return result


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(0).strip() if match else ""


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned.split(":", 1)[-1].strip()
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
