"""JSON-backed localization helpers for the Streamlit group training app."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_LOCALE = "zh_HK"
SUPPORTED_LOCALES = {
    "zh_HK": "\u7e41\u9ad4\u4e2d\u6587",
    "en": "English",
}

_I18N_DIR = Path(__file__).resolve().parent
KEY_ALIASES = {
    "column.average_hidden": "column.average_hidden_score",
    "chart.activity_type": "dashboard.activity_type",
    "chart.activity_count": "dashboard.activity_count",
    "chart.customer_count": "dashboard.customer_count",
    "hidden_score.risk_low": "dashboard.hidden_score_risk_low",
    "hidden_score.risk_medium": "dashboard.hidden_score_risk_medium",
    "hidden_score.risk_high": "dashboard.hidden_score_risk_high",
    "hidden_score.average_by_agent": "dashboard.average_hidden_score_by_agent",
    "hidden_score.rationale": "dashboard.hidden_score_rationale",
}


@lru_cache(maxsize=None)
def load_locale(locale: str) -> dict[str, Any]:
    selected_locale = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    with (_I18N_DIR / f"{selected_locale}.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def translate(locale: str, key: str, **kwargs: Any) -> str:
    key = KEY_ALIASES.get(key, key)
    translations = load_locale(locale)
    text = translations.get(key)
    if text is None and locale != DEFAULT_LOCALE:
        text = load_locale(DEFAULT_LOCALE).get(key)
    if text is None:
        text = translations.get("i18n.fallback") or load_locale(DEFAULT_LOCALE).get("i18n.fallback") or ""
    return text.format(**kwargs) if kwargs else text
