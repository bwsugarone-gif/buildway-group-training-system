# -*- coding: utf-8 -*-
"""
tests/test_ocr_accuracy_upgrade.py
Phase 2.7: OCR Accuracy Upgrade Tests
"""

import pytest
from PIL import Image
import numpy as np

from core.ocr.image_preprocessing import (
    detect_and_crop_document,
    enhance_image_for_ocr,
    preprocess_image_variants,
)
from core.ocr.result_selector import (
    select_best_ocr_result,
    _calculate_text_quality_score,
)


def _create_test_image_with_black_border(doc_size=(100, 100), border=20):
    """Create a test image with white document and black border."""
    width = doc_size[0] + 2 * border
    height = doc_size[1] + 2 * border
    
    # Create image with black background
    image = Image.new("RGB", (width, height), color=(0, 0, 0))
    
    # Add white document region
    for x in range(border, width - border):
        for y in range(border, height - border):
            image.putpixel((x, y), (255, 255, 255))
    
    return image


def _create_small_image():
    """Create a small test image."""
    return Image.new("RGB", (50, 50), color=(200, 200, 200))


def test_crop_helper_does_not_crash_on_black_border_screenshot():
    """Test that crop helper handles black borders without crashing."""
    image = _create_test_image_with_black_border(doc_size=(200, 150), border=30)
    
    # Should not crash
    result = detect_and_crop_document(image)
    
    assert isinstance(result, Image.Image)
    assert result.width <= image.width
    assert result.height <= image.height


def test_crop_helper_does_not_crash_on_small_image():
    """Test that crop helper handles small images without crashing."""
    image = _create_small_image()
    
    # Should not crash and return original
    result = detect_and_crop_document(image)
    
    assert isinstance(result, Image.Image)
    assert result.size == image.size  # Should return original for too-small images


def test_crop_helper_fallback_to_original_on_error():
    """Test that crop helper falls back to original image on any error."""
    image = Image.new("RGB", (100, 100), color=(128, 128, 128))
    
    # Should not crash
    result = detect_and_crop_document(image)
    
    assert isinstance(result, Image.Image)


def test_enhanced_image_larger_than_original():
    """Test that enhanced image is upscaled (3x by default)."""
    image = Image.new("RGB", (100, 80), color=(200, 200, 200))
    
    enhanced = enhance_image_for_ocr(image, scale=3, mode="enhanced")
    
    assert enhanced.width == image.width * 3
    assert enhanced.height == image.height * 3
    assert enhanced.mode == "L"  # Should be grayscale


def test_preprocess_image_variants_generates_all_variants():
    """Test that preprocessing generates all expected variants."""
    image = Image.new("RGB", (100, 100), color=(200, 200, 200))
    
    variants = preprocess_image_variants(image)
    
    assert "original" in variants
    assert "cropped" in variants
    assert "enhanced" in variants
    assert "cropped_enhanced" in variants
    assert all(isinstance(v, Image.Image) for v in variants.values())


def test_enhanced_variant_larger_than_original():
    """Test that enhanced variant is larger than original."""
    image = Image.new("RGB", (50, 50), color=(200, 200, 200))
    
    variants = preprocess_image_variants(image)
    
    assert variants["enhanced"].size[0] > image.size[0]
    assert variants["enhanced"].size[1] > image.size[1]


def test_best_ocr_selector_prefers_text_with_phone_pattern():
    """Test that best OCR selector prioritizes results with phone numbers."""
    results = {
        "original": {
            "extracted_text": "This is some random text without contact info",
            "ocr_status": "SUCCESS",
        },
        "enhanced": {
            "extracted_text": "Name: John Doe\nPhone: 91234567\nEmail: john@example.com",
            "ocr_status": "SUCCESS",
        },
    }
    
    best_variant, best_result = select_best_ocr_result(results)
    
    assert best_variant == "enhanced"
    assert "91234567" in best_result["extracted_text"]


def test_best_ocr_selector_prefers_text_with_email_pattern():
    """Test that best OCR selector prioritizes results with email addresses."""
    results = {
        "original": {
            "extracted_text": "Random text",
            "ocr_status": "SUCCESS",
        },
        "cropped": {
            "extracted_text": "Contact: support@company.com",
            "ocr_status": "SUCCESS",
        },
    }
    
    best_variant, best_result = select_best_ocr_result(results)
    
    assert best_variant == "cropped"
    assert "support@company.com" in best_result["extracted_text"]


def test_best_ocr_selector_skips_empty_results():
    """Test that best OCR selector skips empty or failed results."""
    results = {
        "original": {
            "extracted_text": "",
            "ocr_status": "EMPTY",
        },
        "enhanced": {
            "extracted_text": "Name: Ada Chan\nPhone: 98765432",
            "ocr_status": "SUCCESS",
        },
        "cropped": {
            "extracted_text": "",
            "ocr_status": "FAILED",
        },
    }
    
    best_variant, best_result = select_best_ocr_result(results)
    
    assert best_variant == "enhanced"
    assert best_result["extracted_text"] != ""


def test_best_ocr_selector_prefers_longer_text_when_equal_quality():
    """Test that longer text is preferred when quality scores are similar."""
    results = {
        "original": {
            "extracted_text": "Short",
            "ocr_status": "SUCCESS",
        },
        "enhanced": {
            "extracted_text": "This is a much longer text with more content and information",
            "ocr_status": "SUCCESS",
        },
    }
    
    best_variant, best_result = select_best_ocr_result(results)
    
    assert best_variant == "enhanced"


def test_quality_score_high_for_phone_numbers():
    """Test that quality score is high for text with phone numbers."""
    text_with_phone = "Contact: 91234567"
    text_without_phone = "Random text"
    
    score_with = _calculate_text_quality_score(text_with_phone)
    score_without = _calculate_text_quality_score(text_without_phone)
    
    assert score_with > score_without
    assert score_with >= 10  # Phone pattern adds at least 10 points


def test_quality_score_high_for_email():
    """Test that quality score is high for text with email addresses."""
    text_with_email = "Email: test@example.com"
    text_without_email = "Random text"
    
    score_with = _calculate_text_quality_score(text_with_email)
    score_without = _calculate_text_quality_score(text_without_email)
    
    assert score_with > score_without
    assert score_with >= 10  # Email pattern adds at least 10 points


def test_quality_score_bonus_for_mixed_chinese_english():
    """Test that mixed Chinese/English text gets bonus points."""
    mixed_text = "姓名: John Chan 電話: 91234567"
    english_only = "Name: John Chan Phone: 91234567"
    
    score_mixed = _calculate_text_quality_score(mixed_text)
    score_english = _calculate_text_quality_score(english_only)
    
    # Mixed text should get bonus points (at least 5 for language mix)
    # Plus similar pattern scores
    assert score_mixed >= score_english


def test_upload_flow_uses_best_ocr_text_in_auto_enhanced_mode(monkeypatch):
    """Test that upload flow uses best OCR text when in auto_enhanced mode."""
    from apps.streamlit_group_training.services import ocr_service
    
    captured = {}
    
    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        captured["preprocessing_mode"] = preprocessing_mode
        if preprocessing_mode == "auto_enhanced":
            return {
                "ocr_status": "SUCCESS",
                "extracted_text": "Name: Best Result Customer\nPhone: 91234567\nEmail: best@example.com",
                "warning": "",
                "ocr_message": "OCR extraction successful",
                "preprocessing_mode": "auto_enhanced",
                "best_variant": "cropped_enhanced",
            }
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Name: Regular Customer",
            "warning": "",
            "ocr_message": "OCR extraction successful",
            "preprocessing_mode": preprocessing_mode,
        }
    
    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)
    
    result = ocr_service.extract_text_from_upload(
        b"fake-image",
        "upload.png",
        provider="tesseract",
        preprocessing_mode="auto_enhanced",
    )
    
    assert captured["preprocessing_mode"] == "auto_enhanced"
    assert result.preprocessing_mode == "auto_enhanced"
    assert "Best Result Customer" in result.text
    assert result.status == "success"


def test_no_demo_customer_fallback_in_accuracy_upgrade():
    """Test that accuracy upgrade does not introduce Demo Customer fallbacks."""
    from apps.streamlit_group_training.services import ocr_service
    
    # Empty result should not create Demo Customer
    structured = ocr_service.convert_ocr_text_to_structured_data("", "customer")
    
    assert "Demo Customer" not in str(structured.values())
    assert structured["name"] == ""
    
    # Failed OCR should not create Demo Customer
    result = ocr_service.extract_text_from_upload(
        b"fake-image",
        "unsupported.xyz",
        provider="auto",
    )
    
    assert "Demo Customer" not in result.text
    assert result.status == "unsupported"


def test_crop_removes_black_borders_effectively():
    """Test that crop function removes black borders from screenshots."""
    # Create image: 200x200 white document with 50px black border
    image = _create_test_image_with_black_border(doc_size=(200, 200), border=50)
    
    original_size = image.size  # 300x300
    cropped = detect_and_crop_document(image)
    
    # Cropped should be smaller (black borders removed)
    assert cropped.width < original_size[0]
    assert cropped.height < original_size[1]
    
    # But not too small (document preserved)
    assert cropped.width >= 190  # Allow small margin
    assert cropped.height >= 190


def test_preprocessing_variants_do_not_crash_on_real_world_sizes():
    """Test that preprocessing handles realistic image sizes."""
    # Typical phone screenshot size
    image = Image.new("RGB", (1080, 1920), color=(200, 200, 200))
    
    variants = preprocess_image_variants(image)
    
    assert len(variants) == 4
    assert all(isinstance(v, Image.Image) for v in variants.values())
    
    # Enhanced should be 3x larger
    assert variants["enhanced"].width == 1080 * 3
    assert variants["enhanced"].height == 1920 * 3


def test_best_result_selector_handles_all_failed_variants():
    """Test graceful handling when all variants fail."""
    results = {
        "original": {"extracted_text": "", "ocr_status": "FAILED"},
        "enhanced": {"extracted_text": "", "ocr_status": "EMPTY"},
    }
    
    best_variant, best_result = select_best_ocr_result(results)
    
    # Should return something (fallback behavior)
    assert best_variant in results
    assert isinstance(best_result, dict)


def test_auto_enhanced_default_preprocessing_mode(monkeypatch):
    """Test that tesseract provider defaults to auto_enhanced mode."""
    from apps.streamlit_group_training.services import ocr_service
    
    captured = {}
    
    def fake_extract_text_with_ocr(path, preprocessing_mode="original"):
        captured["preprocessing_mode"] = preprocessing_mode
        return {
            "ocr_status": "SUCCESS",
            "extracted_text": "Test",
            "warning": "",
            "ocr_message": "Success",
            "preprocessing_mode": preprocessing_mode,
        }
    
    monkeypatch.setattr(ocr_service, "_extract_text_with_core_ocr", fake_extract_text_with_ocr)
    
    # Default behavior (no preprocessing_mode specified)
    result = ocr_service.extract_text_from_upload(
        b"fake-image",
        "test.png",
        provider="tesseract",
    )
    
    # Should default to auto_enhanced
    assert captured["preprocessing_mode"] == "auto_enhanced"
    assert result.preprocessing_mode == "auto_enhanced"
