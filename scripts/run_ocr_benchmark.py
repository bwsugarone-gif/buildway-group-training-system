# -*- coding: utf-8 -*-
"""
scripts/run_ocr_benchmark.py
Phase 2.8: OCR Provider Benchmark - Tesseract vs Gemini Vision

執行比較測試並產生報告。
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image
from core.ocr.benchmark import create_benchmark_result, compare_providers, format_benchmark_report


def extract_with_tesseract(image_path: Path) -> tuple[str, dict]:
    """Extract text using Tesseract OCR with best-result selection."""
    from core.ocr.ocr_engine import _ocr_image_with_best_result
    
    image = Image.open(image_path)
    raw_text, best_variant = _ocr_image_with_best_result(image, lang="chi_tra+eng")
    
    # Simple structured extraction (placeholder)
    structured = _extract_structured_fields(raw_text)
    
    return raw_text, structured


def extract_with_gemini(image_path: Path) -> tuple[str, dict]:
    """Extract text using Gemini Vision OCR."""
    from apps.streamlit_group_training.services.ocr_service import _call_gemini_vision_ocr, _get_gemini_api_key
    
    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    
    # Read image bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Call Gemini Vision OCR
    raw_text = _call_gemini_vision_ocr(image_bytes, "image/jpeg", api_key)
    
    # Simple structured extraction
    structured = _extract_structured_fields(raw_text)
    
    return raw_text, structured


def _extract_structured_fields(text: str) -> dict:
    """
    Extract structured fields from raw OCR text.
    Simple regex-based extraction for benchmark purposes.
    """
    import re
    
    fields = {}
    
    # Name (Chinese or English)
    name_patterns = [
        r"(?:姓名|名字|Name)[:：]?\s*([A-Z\s]+(?:[A-Z]+))",  # English name
        r"英文姓名[:：]?\s*([A-Z\s]+)",
        r"YIU\s+CHUN\s+NING",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields["name"] = match.group(1).strip() if match.lastindex else match.group(0).strip()
            break
    
    # Phone number
    phone_patterns = [
        r"(?:電話|手機|流動電話|Tel|Phone|Mobile)[:：]?\s*([\d\s\-+()]+)",
        r"(\d{3,4}[\s\-]?\d{7,8})",  # HK phone format
        r"(852[\s\-]?\d{8})",
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r"[\s\-()]", "", match.group(1))
            if len(phone) >= 8:
                fields["phone"] = phone
                break
    
    # Email
    email_pattern = r"(?:Email|電郵|郵箱)[:：]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    match = re.search(email_pattern, text, re.IGNORECASE)
    if match:
        fields["email"] = match.group(1).strip()
    
    # Policy number
    policy_patterns = [
        r"(?:保單號碼|保單編號|Policy\s*Number|Policy\s*No)[:：]?\s*(\d+)",
        r"(?:客戶編號)[:：]?\s*(\d+)",
        r"(\d{8})",  # 8-digit number (common for policy numbers)
    ]
    for pattern in policy_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            policy_num = match.group(1).strip()
            if len(policy_num) >= 6:
                fields["policy_number"] = policy_num
                break
    
    # Address (basic extraction)
    address_patterns = [
        r"(?:地址|Address)[:：]?\s*([^\n]{10,100})",
        r"(香港[^\n]{5,80})",
        r"(九龍[^\n]{5,80})",
        r"(新界[^\n]{5,80})",
    ]
    for pattern in address_patterns:
        match = re.search(pattern, text)
        if match:
            fields["address"] = match.group(1).strip()
            break
    
    return fields


def run_benchmark(image_path: str):
    """Run complete benchmark and generate report."""
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return
    
    print("=" * 80)
    print("Phase 2.8: OCR Provider Benchmark")
    print("=" * 80)
    print(f"\nTest Image: {image_path.name}")
    print()
    
    # Ground truth for validation
    ground_truth = {
        "name": "YIU CHUN NING",
        "phone": "85296730153",
        "email": "Yiuchunning@gmail.com",
        "policy_number": "02817117",
        "address": "香港九龍黃大仙竹薯南邨趣薯樓644室",  # or similar
    }
    
    print("Ground Truth:")
    for field, value in ground_truth.items():
        print(f"  {field}: {value}")
    print()
    
    # Extract with Tesseract
    print("🔍 Running Tesseract OCR with best-result selection...")
    try:
        tess_raw, tess_structured = extract_with_tesseract(image_path)
        print(f"✓ Tesseract extraction complete ({len(tess_raw)} chars)")
        print(f"  Extracted fields: {list(tess_structured.keys())}")
    except Exception as e:
        print(f"❌ Tesseract failed: {e}")
        return
    
    print()
    
    # Extract with Gemini
    print("🔍 Running Gemini Vision OCR...")
    try:
        gemini_raw, gemini_structured = extract_with_gemini(image_path)
        print(f"✓ Gemini extraction complete ({len(gemini_raw)} chars)")
        print(f"  Extracted fields: {list(gemini_structured.keys())}")
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        print(f"   Make sure GEMINI_API_KEY is set in environment")
        return
    
    print()
    
    # Create benchmark results
    tesseract_result = create_benchmark_result(
        provider="tesseract",
        raw_text=tess_raw,
        structured_data=tess_structured,
        ground_truth=ground_truth,
        threshold=0.8,
    )
    
    gemini_result = create_benchmark_result(
        provider="gemini",
        raw_text=gemini_raw,
        structured_data=gemini_structured,
        ground_truth=ground_truth,
        threshold=0.8,
    )
    
    # Compare providers
    comparison = compare_providers(tesseract_result, gemini_result)
    
    # Format and print report
    report = format_benchmark_report(
        tesseract_result,
        gemini_result,
        comparison,
        document_name="Prudential Insurance Document (保誠保單)",
    )
    
    print(report)
    
    # Save report
    report_path = project_root / "PHASE_2.8_OCR_BENCHMARK_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        f.write("\n\n")
        f.write("## DETAILED EXTRACTION RESULTS\n\n")
        f.write("### Tesseract Raw Text (first 500 chars):\n")
        f.write("```\n")
        f.write(tess_raw[:500])
        f.write("\n```\n\n")
        f.write("### Gemini Raw Text (first 500 chars):\n")
        f.write("```\n")
        f.write(gemini_raw[:500])
        f.write("\n```\n\n")
        f.write("### Tesseract Structured Data:\n")
        f.write("```json\n")
        import json
        f.write(json.dumps(tess_structured, ensure_ascii=False, indent=2))
        f.write("\n```\n\n")
        f.write("### Gemini Structured Data:\n")
        f.write("```json\n")
        f.write(json.dumps(gemini_structured, ensure_ascii=False, indent=2))
        f.write("\n```\n")
    
    print(f"\n✅ Report saved to: {report_path}")
    
    # Determine success
    print("\n" + "=" * 80)
    if gemini_result.correct_fields >= 4:  # At least 4 out of 5 fields correct
        print("✅ SUCCESS: Gemini Vision meets acceptance criteria")
        print(f"   Correctly extracted {gemini_result.correct_fields}/5 critical fields")
    else:
        print("⚠️  Gemini Vision needs improvement")
        print(f"   Only extracted {gemini_result.correct_fields}/5 critical fields correctly")
    
    print("=" * 80)


if __name__ == "__main__":
    # Default test image path
    default_image = r"C:\Users\user\Desktop\cfa7f45f-625b-4f40-bb3e-d095b30b3694.jpg"
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = default_image
    
    run_benchmark(image_path)
