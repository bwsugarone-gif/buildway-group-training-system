# -*- coding: utf-8 -*-
"""
core/ocr/benchmark.py
OCR Provider Benchmark Tool - Compare Tesseract vs Gemini Vision

Generates accuracy comparison reports for insurance document OCR.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldValidation:
    """Validation result for a single field."""
    field_name: str
    expected: str
    extracted: str
    is_correct: bool
    similarity_score: float = 0.0
    notes: str = ""


@dataclass
class BenchmarkResult:
    """Complete benchmark result for one OCR provider."""
    provider: str
    raw_text: str
    structured_data: dict[str, Any]
    validations: list[FieldValidation] = field(default_factory=list)
    total_fields: int = 0
    correct_fields: int = 0
    accuracy_percentage: float = 0.0
    extraction_notes: str = ""


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Remove extra whitespace
    normalized = " ".join(text.split())
    # Remove common punctuation
    normalized = normalized.replace("-", "").replace("(", "").replace(")", "")
    # Lowercase for case-insensitive comparison
    return normalized.strip().lower()


def calculate_field_similarity(expected: str, extracted: str) -> float:
    """
    Calculate similarity score between expected and extracted field values.
    
    Returns:
        Float between 0.0 (no match) and 1.0 (perfect match)
    """
    if not expected and not extracted:
        return 1.0
    if not expected or not extracted:
        return 0.0
    
    norm_expected = normalize_text(expected)
    norm_extracted = normalize_text(extracted)
    
    # Exact match after normalization
    if norm_expected == norm_extracted:
        return 1.0
    
    # Contains check (for addresses, notes, etc.)
    if norm_expected in norm_extracted or norm_extracted in norm_expected:
        # Calculate overlap ratio
        shorter = min(len(norm_expected), len(norm_extracted))
        longer = max(len(norm_expected), len(norm_extracted))
        return shorter / longer if longer > 0 else 0.0
    
    # Character-level similarity for phone numbers, emails
    matching_chars = sum(1 for a, b in zip(norm_expected, norm_extracted) if a == b)
    max_len = max(len(norm_expected), len(norm_extracted))
    return matching_chars / max_len if max_len > 0 else 0.0


def validate_field(field_name: str, expected: str, extracted: str, threshold: float = 0.8) -> FieldValidation:
    """
    Validate a single field extraction.
    
    Args:
        field_name: Name of the field being validated
        expected: Expected/ground truth value
        extracted: Value extracted by OCR
        threshold: Similarity threshold for considering correct (default 0.8)
    
    Returns:
        FieldValidation object with results
    """
    similarity = calculate_field_similarity(expected, extracted)
    is_correct = similarity >= threshold
    
    notes = ""
    if not extracted:
        notes = "Field not extracted"
    elif not expected:
        notes = "No ground truth provided"
    elif not is_correct:
        notes = f"Similarity {similarity:.2f} below threshold {threshold}"
    
    return FieldValidation(
        field_name=field_name,
        expected=expected,
        extracted=extracted,
        is_correct=is_correct,
        similarity_score=similarity,
        notes=notes,
    )


def validate_extraction(
    structured_data: dict[str, Any],
    ground_truth: dict[str, str],
    threshold: float = 0.8,
) -> list[FieldValidation]:
    """
    Validate extracted structured data against ground truth.
    
    Args:
        structured_data: Extracted structured data from OCR
        ground_truth: Dictionary of expected field values
        threshold: Similarity threshold for correctness
    
    Returns:
        List of FieldValidation objects
    """
    validations = []
    
    for field_name, expected_value in ground_truth.items():
        extracted_value = str(structured_data.get(field_name, "")).strip()
        validation = validate_field(field_name, expected_value, extracted_value, threshold)
        validations.append(validation)
    
    return validations


def calculate_accuracy(validations: list[FieldValidation]) -> tuple[int, int, float]:
    """
    Calculate accuracy metrics from validation results.
    
    Returns:
        Tuple of (correct_count, total_count, accuracy_percentage)
    """
    if not validations:
        return 0, 0, 0.0
    
    correct = sum(1 for v in validations if v.is_correct)
    total = len(validations)
    accuracy = (correct / total * 100) if total > 0 else 0.0
    
    return correct, total, accuracy


def create_benchmark_result(
    provider: str,
    raw_text: str,
    structured_data: dict[str, Any],
    ground_truth: dict[str, str],
    threshold: float = 0.8,
) -> BenchmarkResult:
    """
    Create a complete benchmark result with validation.
    
    Args:
        provider: OCR provider name (tesseract/gemini)
        raw_text: Raw OCR text output
        structured_data: Structured/parsed data
        ground_truth: Expected values for validation
        threshold: Similarity threshold
    
    Returns:
        BenchmarkResult object
    """
    validations = validate_extraction(structured_data, ground_truth, threshold)
    correct, total, accuracy = calculate_accuracy(validations)
    
    return BenchmarkResult(
        provider=provider,
        raw_text=raw_text,
        structured_data=structured_data,
        validations=validations,
        total_fields=total,
        correct_fields=correct,
        accuracy_percentage=accuracy,
    )


def compare_providers(
    tesseract_result: BenchmarkResult,
    gemini_result: BenchmarkResult,
) -> dict[str, Any]:
    """
    Compare two provider results and generate comparison report.
    
    Returns:
        Dictionary with comparison metrics and analysis
    """
    comparison = {
        "tesseract": {
            "accuracy": tesseract_result.accuracy_percentage,
            "correct_fields": tesseract_result.correct_fields,
            "total_fields": tesseract_result.total_fields,
        },
        "gemini": {
            "accuracy": gemini_result.accuracy_percentage,
            "correct_fields": gemini_result.correct_fields,
            "total_fields": gemini_result.total_fields,
        },
        "winner": None,
        "accuracy_improvement": 0.0,
        "field_by_field": {},
    }
    
    # Determine winner
    if gemini_result.accuracy_percentage > tesseract_result.accuracy_percentage:
        comparison["winner"] = "gemini"
        comparison["accuracy_improvement"] = (
            gemini_result.accuracy_percentage - tesseract_result.accuracy_percentage
        )
    elif tesseract_result.accuracy_percentage > gemini_result.accuracy_percentage:
        comparison["winner"] = "tesseract"
        comparison["accuracy_improvement"] = (
            tesseract_result.accuracy_percentage - gemini_result.accuracy_percentage
        )
    else:
        comparison["winner"] = "tie"
        comparison["accuracy_improvement"] = 0.0
    
    # Field-by-field comparison
    for tess_val in tesseract_result.validations:
        field_name = tess_val.field_name
        gemini_val = next(
            (v for v in gemini_result.validations if v.field_name == field_name),
            None,
        )
        
        if gemini_val:
            comparison["field_by_field"][field_name] = {
                "tesseract_correct": tess_val.is_correct,
                "gemini_correct": gemini_val.is_correct,
                "tesseract_similarity": tess_val.similarity_score,
                "gemini_similarity": gemini_val.similarity_score,
                "better_provider": (
                    "gemini" if gemini_val.similarity_score > tess_val.similarity_score
                    else "tesseract" if tess_val.similarity_score > gemini_val.similarity_score
                    else "tie"
                ),
            }
    
    return comparison


def format_benchmark_report(
    tesseract_result: BenchmarkResult,
    gemini_result: BenchmarkResult,
    comparison: dict[str, Any],
    document_name: str = "Test Document",
) -> str:
    """
    Format a human-readable benchmark report.
    
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"OCR BENCHMARK REPORT: {document_name}")
    lines.append("=" * 80)
    lines.append("")
    
    # Overall accuracy
    lines.append("## OVERALL ACCURACY")
    lines.append("")
    lines.append(f"Tesseract: {tesseract_result.correct_fields}/{tesseract_result.total_fields} "
                 f"({tesseract_result.accuracy_percentage:.1f}%)")
    lines.append(f"Gemini:    {gemini_result.correct_fields}/{gemini_result.total_fields} "
                 f"({gemini_result.accuracy_percentage:.1f}%)")
    lines.append("")
    
    winner = comparison["winner"]
    improvement = comparison["accuracy_improvement"]
    if winner == "tie":
        lines.append("Result: TIE")
    else:
        lines.append(f"Winner: {winner.upper()} (+{improvement:.1f}% accuracy)")
    lines.append("")
    
    # Field-by-field comparison
    lines.append("## FIELD-BY-FIELD COMPARISON")
    lines.append("")
    lines.append(f"{'Field':<20} {'Tesseract':<12} {'Gemini':<12} {'Better':<10}")
    lines.append("-" * 80)
    
    for field_name, data in comparison["field_by_field"].items():
        tess_status = "✓" if data["tesseract_correct"] else f"✗ ({data['tesseract_similarity']:.2f})"
        gemini_status = "✓" if data["gemini_correct"] else f"✗ ({data['gemini_similarity']:.2f})"
        better = data["better_provider"]
        
        lines.append(f"{field_name:<20} {tess_status:<12} {gemini_status:<12} {better:<10}")
    
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)
