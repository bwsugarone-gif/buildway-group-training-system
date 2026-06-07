import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from apps.streamlit_group_training.i18n.loader import translate


APP_PATH = "apps/streamlit_group_training/app.py"
I18N_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit_group_training" / "i18n"
RAW_KEY_PREFIXES = (
    "nav.",
    "schedule.",
    "training.",
    "dashboard.",
    "risk.",
    "scoring_basis.",
    "chart.",
    "hidden_score.",
    "column.",
    "data.",
    "demo.",
    "filter.",
    "followup.",
    "coaching.",
    "stage_guidance.",
)


def _visible_texts(at: AppTest) -> list[str]:
    texts: list[str] = []
    for collection_name in [
        "title",
        "caption",
        "subheader",
        "markdown",
        "info",
        "warning",
        "success",
        "error",
    ]:
        for element in getattr(at, collection_name):
            value = getattr(element, "value", "")
            if value:
                texts.append(str(value))
    for element in at.button:
        texts.append(element.label)
    for element in at.selectbox:
        texts.append(element.label)
        texts.extend(str(option) for option in element.options)
    for element in at.radio:
        texts.append(element.label)
        texts.extend(str(option) for option in element.options)
    for element in at.metric:
        texts.append(element.label)
    for element in at.expander:
        texts.append(element.label)
    return texts


def _assert_no_raw_i18n_keys(at: AppTest) -> None:
    leaked = [
        text
        for text in _visible_texts(at)
        if text.strip().startswith(RAW_KEY_PREFIXES) or "scoring_basis.item_" in text
    ]
    assert leaked == []


def test_group_training_i18n_json_keys_match_and_fallback_is_safe():
    zh = json.loads((I18N_DIR / "zh_HK.json").read_text(encoding="utf-8"))
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))

    assert set(zh) == set(en)
    assert translate("en", "missing.test.key") == "Translation unavailable"
    assert translate("zh_HK", "column.average_hidden") == "平均隱藏評分"


def test_group_training_streamlit_i18n_smoke_has_no_raw_keys():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=10)
    assert at.title[0].value == "Buildway AI 團隊培訓系統"
    _assert_no_raw_i18n_keys(at)

    at.text_input[0].set_value("admin@buildway.demo")
    at.text_input[1].set_value("Admin123!")
    at.button[0].click()
    at.run(timeout=10)
    _assert_no_raw_i18n_keys(at)

    for page in ["今日行程", "AI 培訓助理", "主管儀表板"]:
        at.radio[0].set_value(page)
        at.run(timeout=10)
        _assert_no_raw_i18n_keys(at)

    at.selectbox[-1].set_value("en")
    at.run(timeout=10)
    assert "Today Schedule" in at.radio[0].options
    _assert_no_raw_i18n_keys(at)
