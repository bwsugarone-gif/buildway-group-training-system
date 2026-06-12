# -*- coding: utf-8 -*-
"""Tests for Phase 2.7 OCR Accuracy Upgrade."""

import pytest
from PIL import Image
from io import BytesIO

from core.ocr.image_preprocessing import detect_and_crop_document, enhance_image_for_ocr, preprocess_image_variants
from core.ocr.result_selector import select_best_ocr_result, _calculate_text_quality_score


def _sample_image(width=200, height=150) -> Image.Image:
    """Create a simple test image."""
    image = Image.new("RGB", (width, height), "white")
    for x in range(image.width):
        for y in range(image.height):
            value = 40 if (x + y) % 2 else 220
            image.putpixel((x, y), (value, value, value))
    return image


def _image_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_crop_helper_does_not_crash():
    """Crop helper should not crash on various inputs."""
    # Normal image
    img = _sample_image(200, 150)
    cropped = detect_and_crop_document(img)
    assert isinstance(cropped, Image.Image)
    
    # Very small image
    tiny = _sample_image(50, 50)
    cropped_tiny = detect_and_crop_document(tiny)
    assert isinstance(cropped_tiny, Image.Image)
    
    # Very dark image (no bright pixels)
    dark = Image.new("RGB", (100, 100), (10, 10, 10))
    cropped_dark = detect_and_crop_document(dark)
    assert isinstance(cropped_dark, Image.Image)


def test_enhanced_image_larger_than_original():
    """Enhanced image should be larger than original (3x scale)."""
    original = _sample_image(100, 80)
    enhanced = enhance_image_for_ocr(original, scale=3, mode="enhanced")
    
    assert enhanced.width == original.width * 3
    assert enhanced.height == original.height * 3
    assert enhanced.mode == "L"  # Grayscale


def test_preprocess_variants_generates_four_variants():
    """preprocess_image_variants should generate 4 variants."""
    image = _sample_image(100, 80)
    variants = preprocess_image_variants(image)
    
    assert "original" in variants
    assert "cropped" in variants
    assert "enhanced" in variants
    assert "cropped_enhanced" in variants
    assert len(variants) == 4


def test_best_ocr_selector_prefers_text_with_phone_email():
    """Best OCR selector should prefer text with phone/email patterns."""
    results = {
        "original": {
            "extracted_text": "Some random text here",
            "ocr_status": "SUCCESS",
        },
        "enhanced": {
            "extracted_text": "Name: Ada Chan\nPhone: 91234567\nEmail: ada@example.com",
            "ocr_status": "SUCCESS",
        },
        "cropped": {
            "extracted_text": "More random text",
            "ocr_status": "SUCCESS",
        },
    }
    
    best_name, best_result = select_best_ocr_result(results)
    
    assert best_name == "enhanced"
    assert "91234567" in best_result["extracted_text"]
    assert "ada@example.com" in best_result["extracted_text"]


def test_quality_score_calculation():
    """Test quality score calculation for OCR text."""
    # Text with phone and email
    text_with_contact = "Name: Ada Chan\nPhone: 91234567\nEmail: ada@example.com"
    score1 = _calculate_text_quality_score(text_with_contact)
    
    # Text without contact info
    text_no_contact = "Some random text here"
    score2 = _calculate_text_quality_score(text_no_contact)
    
    # Score with contact should be much higher
    assert score1 > score2
    assert score1 >= 20  # At least 10 (phone) + 10 (email)


def test_upload_flow_uses_best_ocr_text(monkeypatch):
    """Upload flow should use best OCR text when using auto_enhanced mode."""
    from apps.streamlit_group_training.services import ocr_service
    
    # Mock the core OCR engine to return best_variant
    def fake_extract_text_with_core_ocr(path, preprocessing_mode="original"):
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Best Result Customer\nPhone: 98765432\nEmail: best@example.com",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": "auto_enhanced",
            "best_variant": "cropped_enhanced",
        }
    
    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_core_ocr)
    
    result = ocr_service.extract_text_from_upload(
        _image_bytes(_sample_image()),
        "upload.png",
        preprocessing_mode="auto_enhanced"
    )
    
    assert result.provider == "tesseract"
    assert result.status == "success"
    assert "Best Result Customer" in result.text
    assert result.preprocessing_mode == "auto_enhanced"


def test_no_demo_customer_fallback():
    """Empty/unsupported OCR result should not create Demo Customer fallback."""
    from apps.streamlit_group_training.services.ocr_service import (
        convert_ocr_text_to_structured_data,
        extract_text_from_upload,
    )
    
    # Empty text
    structured = convert_ocr_text_to_structured_data("", "customer")
    assert structured["name"] == ""
    assert structured["phone"] == ""
    assert "Demo Customer" not in str(structured.values())
    
    # Unsupported file
    result = extract_text_from_upload(b"data", "sample.csv")
    assert result.status == "unsupported"
    assert "Demo Customer" not in result.text


def test_auto_enhanced_default_preprocessing_mode(monkeypatch):
    """Default preprocessing mode should be auto_enhanced."""
    from apps.streamlit_group_training.services.ocr_service import _normalize_preprocessing_mode
    
    # No input -> auto_enhanced
    assert _normalize_preprocessing_mode("") == "auto_enhanced"
    assert _normalize_preprocessing_mode(None) == "auto_enhanced"
    
    # Invalid mode -> auto_enhanced
    assert _normalize_preprocessing_mode("invalid_mode") == "auto_enhanced"
    
    # Valid modes preserved
    assert _normalize_preprocessing_mode("original") == "original"
    assert _normalize_preprocessing_mode("enhanced") == "enhanced"
    assert _normalize_preprocessing_mode("auto_enhanced") == "auto_enhanced"
