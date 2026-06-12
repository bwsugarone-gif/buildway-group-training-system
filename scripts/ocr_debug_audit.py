# -*- coding: utf-8 -*-
"""
Phase 2.8.1 OCR Debug Audit
Analyze OCR preprocessing variants and quality scores.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image
from core.ocr.image_preprocessing import preprocess_image_variants
from core.ocr.result_selector import select_best_ocr_result, _calculate_text_quality_score


# Test image path - try multiple locations
TEST_IMAGE_NAME = "cfa7f45f-625b-4f40-bb3e-d095b30b3694.jpg"
TEST_IMAGE_CANDIDATES = [
    project_root / "data" / TEST_IMAGE_NAME,
    Path(r"C:\Users\user\Desktop") / TEST_IMAGE_NAME,
    project_root / TEST_IMAGE_NAME,
]
OUTPUT_DIR = project_root / "output" / "ocr_debug"


def run_ocr_debug_audit():
    """Run comprehensive OCR debug audit."""
    print("=" * 80)
    print("Phase 2.8.1: OCR Debug Audit")
    print("=" * 80)
    print()
    
    # Find test image
    TEST_IMAGE = None
    for candidate in TEST_IMAGE_CANDIDATES:
        if candidate.exists():
            TEST_IMAGE = candidate
            break
    
    if not TEST_IMAGE:
        print(f"❌ Test image not found. Tried:")
        for candidate in TEST_IMAGE_CANDIDATES:
            print(f"   - {candidate}")
        print()
        print("Please place the test image in one of these locations or")
        print("update the TEST_IMAGE_CANDIDATES list in the script.")
        return
    
    print(f"📷 Test Image: {TEST_IMAGE.name}")
    print(f"   Location: {TEST_IMAGE}")
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load original image
    original_image = Image.open(TEST_IMAGE)
    
    print("=" * 80)
    print("IMAGE PREPROCESSING")
    print("=" * 80)
    print()
    
    # Generate variants
    print("🔄 Generating preprocessing variants...")
    variants = preprocess_image_variants(original_image)
    print(f"✓ Generated {len(variants)} variants")
    print()
    
    # Save and analyze each variant
    for variant_name, variant_image in variants.items():
        # Save image
        output_path = OUTPUT_DIR / f"{TEST_IMAGE.stem}_{variant_name}.jpg"
        variant_image.save(output_path, quality=95)
        
        # Print size info
        width, height = variant_image.size
        pixels = width * height
        print(f"📊 {variant_name.upper()}")
        print(f"   Size: {width} x {height} pixels ({pixels:,} total)")
        print(f"   Saved: {output_path.name}")
        print()
    
    print("=" * 80)
    print("OCR EXTRACTION")
    print("=" * 80)
    print()
    
    # Check if Tesseract is available
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        tesseract_available = True
    except Exception as e:
        tesseract_available = False
        print(f"⚠️  Tesseract not available: {e}")
        print()
    
    if not tesseract_available:
        print("=" * 80)
        print("❌ Cannot perform OCR extraction without Tesseract")
        print("   Install Tesseract to complete full audit")
        print("=" * 80)
        return
    
    # Run OCR on each variant
    print("🔍 Running OCR on each variant...")
    print()
    
    ocr_results = {}
    for variant_name, variant_image in variants.items():
        print(f"Processing: {variant_name}...")
        try:
            text = pytesseract.image_to_string(variant_image, lang="chi_tra+eng")
            cleaned_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            
            ocr_results[variant_name] = {
                "extracted_text": cleaned_text,
                "ocr_status": "SUCCESS" if cleaned_text.strip() else "EMPTY",
            }
            
            char_count = len(cleaned_text)
            line_count = len(cleaned_text.splitlines())
            quality_score = _calculate_text_quality_score(cleaned_text)
            
            print(f"✓ {variant_name}: {char_count} chars, {line_count} lines, score={quality_score}")
            
        except Exception as e:
            ocr_results[variant_name] = {
                "extracted_text": "",
                "ocr_status": "FAILED",
                "warning": str(e),
            }
            print(f"✗ {variant_name}: FAILED - {e}")
    
    print()
    
    # Select best result
    print("=" * 80)
    print("BEST RESULT SELECTION")
    print("=" * 80)
    print()
    
    best_variant, best_result = select_best_ocr_result(ocr_results)
    
    print(f"🏆 Selected Best Variant: {best_variant.upper()}")
    print()
    
    # Print detailed results for each variant
    print("=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print()
    
    for variant_name in ["original", "cropped", "enhanced", "cropped_enhanced"]:
        if variant_name not in ocr_results:
            continue
        
        result = ocr_results[variant_name]
        text = result.get("extracted_text", "")
        status = result.get("ocr_status", "UNKNOWN")
        
        is_best = "🏆" if variant_name == best_variant else "  "
        print(f"{is_best} {variant_name.upper()}")
        print(f"   Status: {status}")
        
        if text:
            char_count = len(text)
            line_count = len(text.splitlines())
            quality_score = _calculate_text_quality_score(text)
            
            print(f"   Characters: {char_count}")
            print(f"   Lines: {line_count}")
            print(f"   Quality Score: {quality_score}")
            print()
            print("   Extracted Text Preview:")
            print("   " + "-" * 76)
            preview_lines = text.splitlines()[:10]
            for line in preview_lines:
                print(f"   {line[:74]}")
            if len(text.splitlines()) > 10:
                print(f"   ... ({len(text.splitlines()) - 10} more lines)")
            print("   " + "-" * 76)
        else:
            print(f"   (No text extracted)")
            if "warning" in result:
                print(f"   Warning: {result['warning']}")
        
        print()
    
    # Save full results
    results_file = OUTPUT_DIR / f"{TEST_IMAGE.stem}_ocr_results.txt"
    with open(results_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("Phase 2.8.1 OCR Debug Audit Results\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Test Image: {TEST_IMAGE.name}\n")
        f.write(f"Best Variant: {best_variant}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("FULL OCR RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        for variant_name in ["original", "cropped", "enhanced", "cropped_enhanced"]:
            if variant_name not in ocr_results:
                continue
            
            result = ocr_results[variant_name]
            text = result.get("extracted_text", "")
            
            f.write(f"[{variant_name.upper()}]\n")
            f.write("-" * 80 + "\n")
            if text:
                f.write(text)
                f.write("\n")
            else:
                f.write("(No text extracted)\n")
            f.write("\n" + "=" * 80 + "\n\n")
    
    print("=" * 80)
    print(f"✅ Audit complete. Results saved to:")
    print(f"   {OUTPUT_DIR}")
    print(f"   - {results_file.name}")
    for variant_name in variants.keys():
        print(f"   - {TEST_IMAGE.stem}_{variant_name}.jpg")
    print("=" * 80)


if __name__ == "__main__":
    run_ocr_debug_audit()
