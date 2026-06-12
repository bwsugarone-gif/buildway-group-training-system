# -*- coding: utf-8 -*-
"""
core/ocr/image_preprocessing.py
Advanced image preprocessing for OCR accuracy improvement.
Includes document region detection, cropping, and enhancement.
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def _resample_filter() -> int:
    """Get best available resample filter for Pillow."""
    return getattr(getattr(Image, "Resampling", Image), "LANCZOS")


def detect_and_crop_document(image: Image.Image) -> Image.Image:
    """
    Detect document region in screenshot and crop out black borders/noise.
    Falls back to original image if detection fails.
    
    Strategy:
    - Find largest bright (white/light) rectangular region
    - Remove black borders from screenshots
    - Preserve full document area
    """
    try:
        # Convert to numpy for processing
        img_array = np.array(image.convert("L"))
        height, width = img_array.shape
        
        # Quick validation: if image too small, skip
        if width < 100 or height < 100:
            return image
        
        # Find bright regions (document is typically white/light)
        # Threshold: pixels > 180 are considered "bright"
        bright_mask = img_array > 180
        
        # If not enough bright pixels, return original
        bright_ratio = np.sum(bright_mask) / (width * height)
        if bright_ratio < 0.05:  # Less than 5% bright pixels
            return image
        
        # Find bounding box of bright regions
        rows = np.any(bright_mask, axis=1)
        cols = np.any(bright_mask, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            return image
        
        row_indices = np.where(rows)[0]
        col_indices = np.where(cols)[0]
        
        top = row_indices[0]
        bottom = row_indices[-1]
        left = col_indices[0]
        right = col_indices[-1]
        
        # Add small margin (2% of each dimension)
        margin_h = int((bottom - top) * 0.02)
        margin_w = int((right - left) * 0.02)
        
        top = max(0, top - margin_h)
        bottom = min(height - 1, bottom + margin_h)
        left = max(0, left - margin_w)
        right = min(width - 1, right + margin_w)
        
        # Validate crop region is meaningful
        crop_height = bottom - top
        crop_width = right - left
        
        # If crop is too small or too similar to original, skip
        if crop_height < height * 0.3 or crop_width < width * 0.3:
            return image
        
        if crop_height > height * 0.95 and crop_width > width * 0.95:
            return image
        
        # Perform crop
        cropped = image.crop((left, top, right, bottom))
        return cropped
        
    except Exception:
        # On any error, return original
        return image


def enhance_image_for_ocr(image: Image.Image, scale: int = 3, mode: str = "enhanced") -> Image.Image:
    """
    Enhance image for better OCR accuracy.
    
    Args:
        image: Input PIL Image
        scale: Upscale factor (default 3x)
        mode: 'enhanced' (default) or 'high_contrast'
    
    Returns:
        Enhanced PIL Image
    """
    # Resize (upscale for better OCR)
    new_width = image.width * scale
    new_height = image.height * scale
    resized = image.resize((new_width, new_height), _resample_filter())
    
    # Convert to grayscale
    grayscale = resized.convert("L")
    
    if mode == "high_contrast":
        # High contrast mode: aggressive threshold
        sharpened = grayscale.filter(ImageFilter.SHARPEN)
        contrasted = ImageEnhance.Contrast(sharpened).enhance(2.2)
        # Binary threshold
        return contrasted.point(lambda pixel: 255 if pixel >= 160 else 0)
    
    # Default enhanced mode
    contrasted = ImageEnhance.Contrast(grayscale).enhance(1.8)
    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    return sharpened


def preprocess_image_variants(image: Image.Image) -> dict[str, Image.Image]:
    """
    Generate multiple preprocessed variants for best-result selection.
    
    Returns dict with keys: 'original', 'cropped', 'enhanced', 'cropped_enhanced'
    """
    variants = {}
    
    # Original
    variants["original"] = image
    
    # Cropped only
    cropped = detect_and_crop_document(image)
    variants["cropped"] = cropped
    
    # Enhanced only (no crop)
    enhanced = enhance_image_for_ocr(image, scale=3, mode="enhanced")
    variants["enhanced"] = enhanced
    
    # Cropped + Enhanced (best combination)
    cropped_enhanced = enhance_image_for_ocr(cropped, scale=3, mode="enhanced")
    variants["cropped_enhanced"] = cropped_enhanced
    
    return variants
