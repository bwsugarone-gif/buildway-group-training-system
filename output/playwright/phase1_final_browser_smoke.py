from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "playwright"
URL = "http://localhost:8524"
IMAGE = OUT / "phase-1-final-ocr-sample.png"


RAW_PATTERN = re.compile(
    r"(\[missing translation|(?<![A-Za-z0-9_])(?:dashboard|chart|ocr|nav|schedule|training|hidden_score|column)\.[A-Za-z0-9_]+)"
)


def write_sample_image() -> None:
    image = Image.new("RGB", (640, 360), "white")
    image.save(IMAGE)


def assert_clean(page: Page, label: str) -> None:
    body = page.locator("body").inner_text()
    matches = sorted(set(RAW_PATTERN.findall(body)))
    if matches:
        raise AssertionError(f"{label} raw i18n keys: {matches}")


def screenshot(page: Page, name: str) -> None:
    page.screenshot(path=str(OUT / name), full_page=False)


def open_page(page: Page, label: str) -> None:
    page.get_by_text(label, exact=True).first.click()
    page.wait_for_timeout(1200)


def login(page: Page, email: str, password: str) -> None:
    page.goto(URL, wait_until="domcontentloaded")
    expect(page.get_by_role("button", name="登入")).to_be_visible(timeout=20000)
    screenshot(page, "phase-1-final-login.png")
    page.get_by_label("電郵").fill(email)
    page.get_by_label("密碼").fill(password)
    page.get_by_role("button", name="登入").click()
    expect(page.get_by_text("客戶管理", exact=True).first).to_be_visible(timeout=20000)


def main() -> None:
    write_sample_image()
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        login(page, "admin@buildway.demo", "Admin123!")
        assert_clean(page, "crm")
        screenshot(page, "phase-1-final-crm.png")

        open_page(page, "每日工作記錄")
        assert_clean(page, "daily-log")
        screenshot(page, "phase-1-final-daily-log.png")

        open_page(page, "主管儀表板")
        assert_clean(page, "dashboard-zh")
        screenshot(page, "phase-1-final-dashboard-zh.png")

        page.get_by_label("語言").click()
        page.get_by_text("English", exact=True).click()
        expect(page.get_by_text("Manager Dashboard", exact=True).first).to_be_visible(timeout=20000)
        assert_clean(page, "dashboard-en")
        screenshot(page, "phase-1-final-dashboard-en.png")

        open_page(page, "OCR Data Capture")
        assert_clean(page, "ocr-upload-empty")
        page.locator("input[type='file']").set_input_files(str(IMAGE))
        expect(page.get_by_text("Image preview", exact=True)).to_be_visible(timeout=20000)
        screenshot(page, "phase-1-final-ocr-upload.png")
        page.get_by_role("button", name="Start extraction").click()
        expect(page.get_by_text("Structured result", exact=True)).to_be_visible(timeout=20000)
        assert_clean(page, "ocr-result")
        screenshot(page, "phase-1-final-ocr-result.png")
        page.get_by_role("button", name="Confirm Save").click()
        expect(page.get_by_text("OCR data saved.", exact=True)).to_be_visible(timeout=20000)
        assert_clean(page, "ocr-save")
        screenshot(page, "phase-1-final-ocr-save.png")

        # Agent permission smoke: dashboard nav should not be visible after agent login.
        page.get_by_role("button", name="Logout").click()
        expect(page.get_by_role("button", name="Login")).to_be_visible(timeout=20000)
        page.get_by_role("textbox", name="Email").fill("agent@buildway.demo")
        page.get_by_role("textbox", name="Password").fill("Agent123!")
        page.get_by_role("button", name="Login").click()
        expect(page.get_by_text("Customer CRM", exact=True).first).to_be_visible(timeout=20000)
        results["agent_dashboard_nav_visible"] = page.get_by_text("Manager Dashboard", exact=True).count() > 0

        # Mobile width smoke.
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(1000)
        metrics = page.evaluate(
            "() => ({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})"
        )
        results["mobile_overflow"] = metrics["scrollWidth"] > metrics["clientWidth"] + 4
        browser.close()

    results["screenshots"] = sorted(path.name for path in OUT.glob("phase-1-final-*.png"))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
