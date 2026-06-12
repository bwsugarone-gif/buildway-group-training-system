# -*- coding: utf-8 -*-
"""
OCR Emergency Audit Tool

不修改任何功能，只做診斷。
輸出所有中間步驟圖片、文字、分數，以便人工檢查。
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image

# Ensure debug directory exists
DEBUG_DIR = Path("debug/ocr")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def save_debug_image(image: Image.Image, filename: str) -> Path:
    """Save debug image to debug/ocr/ directory."""
    path = DEBUG_DIR / filename
    image.save(path)
    return path


def save_debug_text(text: str, filename: str) -> Path:
    """Save debug text to debug/ocr/ directory."""
    path = DEBUG_DIR / filename
    path.write_text(text, encoding="utf-8")
    return path


def calculate_ocr_quality_score(text: str) -> dict[str, Any]:
    """Calculate OCR quality metrics."""
    # Phone patterns (Hong Kong style)
    phone_patterns = [
        r"\+852\s*\d{8}",  # +852 format
        r"\b[5-9]\d{7}\b",  # 8-digit starting with 5-9
        r"\b\d{4}[-\s]?\d{4}\b",  # 4-4 format
        r"\b852\d{8,11}\b",  # 852 prefix
    ]
    phone_matches = []
    for pattern in phone_patterns:
        phone_matches.extend(re.findall(pattern, text))
    
    # Email patterns
    email_pattern = r"[\w.\-+]+@[\w.\-]+\.\w+"
    email_matches = re.findall(email_pattern, text, re.IGNORECASE)
    
    # Date patterns
    date_pattern = r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"
    date_matches = re.findall(date_pattern, text)
    
    # Key-value structure
    kv_pattern = r"[\w\u4e00-\u9fff]+\s*[:：]\s*.+"
    kv_matches = re.findall(kv_pattern, text)
    
    # Calculate score
    score = 0
    score += len(phone_matches) * 10
    score += len(email_matches) * 10
    score += len(date_matches) * 3
    score += len(kv_matches) * 2
    score += min(len(re.findall(r"\b\d+\b", text)), 20)
    
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_english = bool(re.search(r"[a-zA-Z]", text))
    if has_chinese and has_english:
        score += 5
    
    return {
        "score": score,
        "text_length": len(text),
        "phone_matches": phone_matches,
        "phone_count": len(phone_matches),
        "email_matches": email_matches,
        "email_count": len(email_matches),
        "date_matches": date_matches,
        "date_count": len(date_matches),
        "kv_count": len(kv_matches),
        "has_chinese": has_chinese,
        "has_english": has_english,
    }


def check_expected_data(text: str) -> dict[str, bool]:
    """Check if expected data appears in OCR text."""
    text_upper = text.upper()
    
    # Expected data
    expected_name = "YIU CHUN NING"
    expected_phone = "85296730153"
    expected_email = "YIUCHUNNING@GMAIL.COM"
    
    return {
        "name_found": expected_name in text_upper or "YIU" in text_upper,
        "phone_found": expected_phone in text or "96730153" in text or "852 96730153" in text,
        "email_found": expected_email in text_upper or "YIUCHUNNING" in text_upper,
        "name_exact": expected_name in text_upper,
        "phone_exact": expected_phone in text,
        "email_exact": expected_email in text_upper,
    }


def run_ocr_on_image(image: Image.Image, mode: str = "original") -> dict[str, Any]:
    """Run OCR on a single image and return text + metadata."""
    try:
        import pytesseract
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            image.save(tmp.name)
            tmp_path = Path(tmp.name)
        
        try:
            # Run OCR
            text = pytesseract.image_to_string(image, lang="chi_tra+eng")
            
            return {
                "status": "success",
                "text": text,
                "error": None,
            }
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
    
    except Exception as e:
        return {
            "status": "failed",
            "text": "",
            "error": str(e),
        }


def generate_audit_report(audit_data: dict[str, Any]) -> str:
    """Generate audit report in Markdown format."""
    report = []
    report.append("# OCR Emergency Audit Report\n")
    report.append(f"Generated: {audit_data.get('timestamp', 'N/A')}\n")
    report.append("\n## 上傳圖片資訊\n")
    report.append(f"- **原始檔名**: {audit_data.get('original_filename', 'N/A')}\n")
    report.append(f"- **原始尺寸**: {audit_data.get('original_width', 0)} x {audit_data.get('original_height', 0)}\n")
    
    report.append("\n## 四種預處理模式結果\n")
    
    for variant in ["original", "cropped", "enhanced", "cropped_enhanced"]:
        variant_data = audit_data.get(variant, {})
        report.append(f"\n### {variant.upper()}\n")
        report.append(f"- **尺寸**: {variant_data.get('width', 0)} x {variant_data.get('height', 0)}\n")
        report.append(f"- **OCR 狀態**: {variant_data.get('ocr_status', 'N/A')}\n")
        report.append(f"- **文字長度**: {variant_data.get('text_length', 0)}\n")
        report.append(f"- **Quality Score**: {variant_data.get('score', 0)}\n")
        report.append(f"- **電話匹配**: {variant_data.get('phone_count', 0)} ({variant_data.get('phone_matches', [])})\n")
        report.append(f"- **Email 匹配**: {variant_data.get('email_count', 0)} ({variant_data.get('email_matches', [])})\n")
    
    report.append("\n## Best Selector 選擇結果\n")
    report.append(f"- **最終採用**: {audit_data.get('best_variant', 'N/A')}\n")
    report.append(f"- **選擇原因**: Score 最高 ({audit_data.get('best_score', 0)})\n")
    
    report.append("\n## 驗證預期資料\n")
    expected = audit_data.get('expected_data_check', {})
    report.append(f"- **姓名 (YIU CHUN NING)**: {'✓ 找到' if expected.get('name_found') else '✗ 未找到'}\n")
    report.append(f"- **電話 (85296730153)**: {'✓ 找到' if expected.get('phone_found') else '✗ 未找到'}\n")
    report.append(f"- **Email (Yiuchunning@gmail.com)**: {'✓ 找到' if expected.get('email_found') else '✗ 未找到'}\n")
    
    report.append("\n## 診斷結論\n")
    
    # Crop 是否裁錯
    original_data = audit_data.get('original', {})
    cropped_data = audit_data.get('cropped', {})
    crop_ratio = cropped_data.get('width', 1) / max(original_data.get('width', 1), 1)
    
    if crop_ratio < 0.3:
        report.append("- **Crop 診斷**: ⚠️ 可能裁錯 - 裁剪後尺寸過小 (< 30% 原圖)\n")
    elif crop_ratio > 0.95:
        report.append("- **Crop 診斷**: ℹ️ 未裁剪 - 未偵測到明顯黑邊\n")
    else:
        report.append("- **Crop 診斷**: ✓ 裁剪正常\n")
    
    # Best selector 是否選錯
    best_variant = audit_data.get('best_variant', '')
    best_score = audit_data.get('best_score', 0)
    all_scores = {
        variant: audit_data.get(variant, {}).get('score', 0)
        for variant in ["original", "cropped", "enhanced", "cropped_enhanced"]
    }
    max_score_variant = max(all_scores, key=all_scores.get)
    
    if best_variant == max_score_variant:
        report.append(f"- **Best Selector 診斷**: ✓ 選擇正確 - 選擇了分數最高的 {best_variant}\n")
    else:
        report.append(f"- **Best Selector 診斷**: ⚠️ 可能選錯 - 選擇了 {best_variant} (score={best_score})，但 {max_score_variant} 分數更高 (score={all_scores[max_score_variant]})\n")
    
    # OCR engine 是否讀錯
    if not expected.get('name_found') and not expected.get('phone_found') and not expected.get('email_found'):
        report.append("- **OCR Engine 診斷**: ✗ 完全未讀到預期資料 - OCR 可能失敗或圖片問題\n")
    elif expected.get('name_found') and expected.get('phone_found') and expected.get('email_found'):
        report.append("- **OCR Engine 診斷**: ✓ 成功讀取所有預期資料\n")
    else:
        missing = []
        if not expected.get('name_found'):
            missing.append("姓名")
        if not expected.get('phone_found'):
            missing.append("電話")
        if not expected.get('email_found'):
            missing.append("Email")
        report.append(f"- **OCR Engine 診斷**: ⚠️ 部分資料遺失 - 未找到: {', '.join(missing)}\n")
    
    # DeepSeek extraction 診斷
    deepseek_data = audit_data.get('deepseek_result', {})
    if deepseek_data:
        report.append("- **DeepSeek Extraction 診斷**: ℹ️ 已執行結構化提取\n")
        report.append(f"  - 提取姓名: {deepseek_data.get('name', 'N/A')}\n")
        report.append(f"  - 提取電話: {deepseek_data.get('phone', 'N/A')}\n")
        report.append(f"  - 提取Email: {deepseek_data.get('email', 'N/A')}\n")
    else:
        report.append("- **DeepSeek Extraction 診斷**: ℹ️ 未執行或無結果\n")
    
    report.append("\n## 建議行動\n")
    report.append("1. 檢查 debug/ocr/ 目錄中的四張圖片，確認裁剪和增強是否正確\n")
    report.append("2. 檢查四個 OCR 文字檔，確認哪一個識別最準確\n")
    report.append("3. 如果所有 OCR 結果都不準確，可能是 Tesseract 語言包或圖片品質問題\n")
    report.append("4. 如果 OCR 準確但結構化提取失敗，需要檢查 DeepSeek prompt\n")
    
    return "".join(report)


def main():
    """Main Streamlit app for OCR Debug Audit."""
    st.title("🔍 OCR Emergency Audit Tool")
    st.caption("診斷 OCR Pipeline - 不修改任何功能，只輸出診斷資訊")
    
    st.warning("⚠️ 此工具僅供診斷，不會修改任何現有功能")
    
    uploaded_file = st.file_uploader(
        "上傳保單圖片進行診斷",
        type=["png", "jpg", "jpeg"],
        help="上傳同一張保單圖片，系統會輸出完整診斷報告"
    )
    
    if uploaded_file:
        st.success(f"已上傳: {uploaded_file.name}")
        
        # Load image
        image_bytes = uploaded_file.read()
        original_image = Image.open(uploaded_file)
        
        st.info(f"原始尺寸: {original_image.width} x {original_image.height}")
        
        if st.button("🚀 開始 OCR Audit", type="primary"):
            with st.spinner("正在執行 OCR Audit..."):
                import datetime
                from core.ocr.image_preprocessing import preprocess_image_variants
                
                audit_data = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "original_filename": uploaded_file.name,
                    "original_width": original_image.width,
                    "original_height": original_image.height,
                }
                
                # Generate all variants
                variants = preprocess_image_variants(original_image)
                
                st.subheader("1️⃣ 四種預處理模式")
                
                all_ocr_results = {}
                
                for variant_name, variant_image in variants.items():
                    st.write(f"**{variant_name.upper()}**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Save image
                        img_path = save_debug_image(variant_image, f"{variant_name}.png")
                        st.image(variant_image, caption=f"{variant_name} ({variant_image.width}x{variant_image.height})", use_container_width=True)
                        st.caption(f"✓ 已儲存: {img_path}")
                    
                    with col2:
                        # Run OCR
                        ocr_result = run_ocr_on_image(variant_image)
                        ocr_text = ocr_result.get("text", "")
                        
                        # Save text
                        text_path = save_debug_text(ocr_text, f"{variant_name}_text.txt")
                        
                        # Calculate quality
                        quality = calculate_ocr_quality_score(ocr_text)
                        
                        st.metric("尺寸", f"{variant_image.width} x {variant_image.height}")
                        st.metric("文字長度", quality["text_length"])
                        st.metric("Quality Score", quality["score"])
                        st.metric("電話匹配", quality["phone_count"])
                        st.metric("Email 匹配", quality["email_count"])
                        
                        st.caption(f"✓ 已儲存: {text_path}")
                        
                        # Store results
                        audit_data[variant_name] = {
                            "width": variant_image.width,
                            "height": variant_image.height,
                            "ocr_status": ocr_result["status"],
                            "text": ocr_text,
                            **quality,
                        }
                        all_ocr_results[variant_name] = {
                            "extracted_text": ocr_text,
                            "ocr_status": "SUCCESS" if ocr_text else "EMPTY",
                        }
                
                # Best result selection
                from core.ocr.result_selector import select_best_ocr_result
                
                best_variant, best_result = select_best_ocr_result(all_ocr_results)
                best_text = best_result.get("extracted_text", "")
                best_quality = calculate_ocr_quality_score(best_text)
                
                audit_data["best_variant"] = best_variant
                audit_data["best_score"] = best_quality["score"]
                
                st.subheader("2️⃣ Best Selector 選擇結果")
                st.success(f"✓ 最終採用: **{best_variant.upper()}** (Score: {best_quality['score']})")
                
                # Verify expected data
                st.subheader("3️⃣ 驗證預期資料")
                expected_check = check_expected_data(best_text)
                audit_data["expected_data_check"] = expected_check
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if expected_check["name_found"]:
                        st.success("✓ 姓名: YIU CHUN NING")
                    else:
                        st.error("✗ 姓名未找到")
                
                with col2:
                    if expected_check["phone_found"]:
                        st.success("✓ 電話: 85296730153")
                    else:
                        st.error("✗ 電話未找到")
                
                with col3:
                    if expected_check["email_found"]:
                        st.success("✓ Email: Yiuchunning@gmail.com")
                    else:
                        st.error("✗ Email 未找到")
                
                # Generate audit report
                st.subheader("4️⃣ Audit Report")
                report_md = generate_audit_report(audit_data)
                report_path = save_debug_text(report_md, "audit_report.md")
                
                st.markdown(report_md)
                st.success(f"✓ 完整報告已儲存: {report_path}")
                
                st.info("📁 所有診斷檔案已儲存到 debug/ocr/ 目錄")


if __name__ == "__main__":
    main()
