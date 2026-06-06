# -*- coding: utf-8 -*-
"""
core/agents/evidence_confidence.py
Buildway AI Core — Evidence Confidence Scoring

Scores how much usable evidence is present in uploaded files
before committing to a full AI analysis run.
"""

from pathlib import Path
from typing import Any


# Minimum character count to consider a file as having usable text
MIN_TEXT_CHARS = 50

# Confidence levels
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_NONE = "none"


def score_file(file_result: dict[str, Any]) -> dict[str, Any]:
    """
    Score a single file's evidence quality.

    Args:
        file_result: Dict from file_loader.load_file() or ocr_engine.extract_text_with_ocr().
            Expected keys: text (or extracted_text), type, name.

    Returns:
        Dict with keys: confidence, char_count, has_text, notes.
    """
    text = file_result.get("text") or file_result.get("extracted_text") or ""
    char_count = len(text.strip())
    file_type = str(file_result.get("type") or file_result.get("file_type") or "").lower()
    name = str(file_result.get("name") or file_result.get("file_path") or "")

    notes = []

    # Images always have low text confidence (rely on OCR or visual analysis)
    if any(ext in name.lower() for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]):
        if char_count < MIN_TEXT_CHARS:
            return {
                "confidence": CONFIDENCE_LOW,
                "char_count": char_count,
                "has_text": False,
                "notes": ["Image file with no extracted text. Visual analysis only."],
            }
        notes.append("Image file with OCR text extracted.")

    if char_count == 0:
        return {
            "confidence": CONFIDENCE_NONE,
            "char_count": 0,
            "has_text": False,
            "notes": ["No text content found in file."],
        }

    if char_count < MIN_TEXT_CHARS:
        return {
            "confidence": CONFIDENCE_LOW,
            "char_count": char_count,
            "has_text": True,
            "notes": [f"Very little text ({char_count} chars). Analysis may be unreliable."],
        }

    if char_count < 500:
        confidence = CONFIDENCE_MEDIUM
        notes.append(f"Limited text ({char_count} chars).")
    else:
        confidence = CONFIDENCE_HIGH
        notes.append(f"Sufficient text ({char_count} chars).")

    return {
        "confidence": confidence,
        "char_count": char_count,
        "has_text": True,
        "notes": notes,
    }


def score_files(file_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Score evidence quality across multiple files.

    Returns:
        Dict with keys: overall_confidence, file_scores, total_chars,
                        has_any_text, gate_passed, notes.
    """
    if not file_results:
        return {
            "overall_confidence": CONFIDENCE_NONE,
            "file_scores": [],
            "total_chars": 0,
            "has_any_text": False,
            "gate_passed": False,
            "notes": ["No files provided."],
        }

    file_scores = [score_file(f) for f in file_results]
    total_chars = sum(s["char_count"] for s in file_scores)
    has_any_text = any(s["has_text"] for s in file_scores)

    # Overall confidence = best single-file confidence
    confidence_rank = {CONFIDENCE_HIGH: 3, CONFIDENCE_MEDIUM: 2, CONFIDENCE_LOW: 1, CONFIDENCE_NONE: 0}
    best = max(file_scores, key=lambda s: confidence_rank.get(s["confidence"], 0))
    overall = best["confidence"]

    gate_passed = overall in {CONFIDENCE_HIGH, CONFIDENCE_MEDIUM}

    notes = []
    if not gate_passed:
        notes.append("Evidence gate not passed. Insufficient text for reliable analysis.")
    if total_chars > 0:
        notes.append(f"Total extractable text: {total_chars} chars across {len(file_results)} file(s).")

    return {
        "overall_confidence": overall,
        "file_scores": file_scores,
        "total_chars": total_chars,
        "has_any_text": has_any_text,
        "gate_passed": gate_passed,
        "notes": notes,
    }
