# -*- coding: utf-8 -*-
"""
core/ocr/result_selector.py
Select best OCR result from multiple preprocessing variants.
"""

import re
from typing import Any


def select_best_ocr_result(results: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """
    Select the best OCR result from multiple preprocessing variants.
    
    Args:
        results: Dict mapping variant name -> OCR result dict
                 e.g., {"original": {...}, "enhanced": {...}, "cropped_enhanced": {...}}
    
    Returns:
        Tuple of (best_variant_name, best_result_dict)
    
    Selection criteria (in order):
    1. Text with most phone/email patterns (highest signal of real content)
    2. Longest non-empty text
    3. First available result
    """
    if not results:
        return "original", {"extracted_text": "", "ocr_status": "FAILED"}
    
    scored = []
    
    for variant_name, result in results.items():
        text = str(result.get("extracted_text", ""))
        
        # Skip empty or failed results
        if not text.strip() or result.get("ocr_status", "").upper() in {"FAILED", "EMPTY", "UNAVAILABLE"}:
            continue
        
        score = _calculate_text_quality_score(text)
        scored.append((score, len(text), variant_name, result))
    
    # Sort by: (quality_score desc, length desc)
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    
    if scored:
        _, _, best_name, best_result = scored[0]
        return best_name, best_result
    
    # Fallback: return first available result even if empty
    for variant_name in ["cropped_enhanced", "enhanced", "cropped", "original"]:
        if variant_name in results:
            return variant_name, results[variant_name]
    
    # Last resort
    first_key = next(iter(results))
    return first_key, results[first_key]


def _calculate_text_quality_score(text: str) -> int:
    """
    Calculate quality score for OCR text based on structured data patterns.
    
    Returns integer score (higher is better).
    """
    score = 0
    
    # Phone patterns (Hong Kong style)
    # +852 91234567, 91234567, 9123-4567, etc.
    phone_patterns = [
        r"\+852\s*\d{8}",  # +852 format
        r"\b[5-9]\d{7}\b",  # 8-digit starting with 5-9
        r"\b\d{4}[-\s]?\d{4}\b",  # 4-4 format
    ]
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        score += len(matches) * 10  # Each phone = +10 points
    
    # Email patterns
    email_pattern = r"[\w.\-+]+@[\w.\-]+\.\w+"
    email_matches = re.findall(email_pattern, text)
    score += len(email_matches) * 10  # Each email = +10 points
    
    # Date patterns (YYYY-MM-DD, YYYY/MM/DD)
    date_pattern = r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"
    date_matches = re.findall(date_pattern, text)
    score += len(date_matches) * 3  # Each date = +3 points
    
    # Key-value structure (Name:, Phone:, etc.)
    kv_pattern = r"[\w\u4e00-\u9fff]+\s*[:：]\s*.+"
    kv_matches = re.findall(kv_pattern, text)
    score += len(kv_matches) * 2  # Each key-value = +2 points
    
    # Numbers (activity counts, etc.)
    number_pattern = r"\b\d+\b"
    number_matches = re.findall(number_pattern, text)
    score += min(len(number_matches), 20)  # Cap at 20 points
    
    # Chinese/English mixed text (good for HK documents)
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_english = bool(re.search(r"[a-zA-Z]", text))
    if has_chinese and has_english:
        score += 5
    
    return score
