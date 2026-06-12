# -*- coding: utf-8 -*-
"""
test_gemini_real_ocr.py
實際測試 Gemini Vision OCR 功能
"""

import os
from pathlib import Path

# Set API key from .env
from dotenv import load_dotenv
load_dotenv()

# Set required env vars
os.environ["ENABLE_PAID_OCR"] = "true"
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

from apps.streamlit_group_training.services import ocr_service


def test_gemini_ocr_with_real_image():
    """Test Gemini OCR with actual image file."""
    
    # Find test image
    test_image_paths = [
        Path("data/test_images/prudential_screenshot.png"),
        Path("data/test_images/test_insurance_doc.png"),
        Path("assets/test_insurance_doc.png"),
        Path("testing/test_insurance_doc.png"),
    ]
    
    image_path = None
    for path in test_image_paths:
        if path.exists():
            image_path = path
            break
    
    if not image_path:
        print("❌ No test image found. Please provide path to insurance document screenshot.")
        print("Checked paths:")
        for p in test_image_paths:
            print(f"  - {p}")
        return
    
    print(f"📄 Using test image: {image_path}")
    print(f"📁 File size: {image_path.stat().st_size} bytes")
    print()
    
    # Read image bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Call OCR with Gemini provider
    print("🚀 Calling Gemini Vision OCR...")
    print("=" * 60)
    
    result = ocr_service.extract_text_from_upload(
        file_bytes=image_bytes,
        filename=image_path.name,
        provider="gemini",
        paid_ocr_allowed_by_role=True,
    )
    
    print()
    print("=" * 60)
    print("📊 OCR RESULT:")
    print("=" * 60)
    print(f"Provider: {result.provider}")
    print(f"Status: {result.status}")
    print(f"Cost Mode: {result.cost_mode}")
    print(f"Error: {result.error}")
    print()
    print("=" * 60)
    print("📝 OCR RAW TEXT:")
    print("=" * 60)
    print(result.text)
    print()
    print("=" * 60)
    print("🔍 STRUCTURED EXTRACTION:")
    print("=" * 60)
    
    # Convert to structured data
    structured = ocr_service.convert_ocr_text_to_structured_data(result.text, "customer")
    
    import json
    print(json.dumps(structured, ensure_ascii=False, indent=2))
    
    print()
    print("=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_gemini_ocr_with_real_image()
