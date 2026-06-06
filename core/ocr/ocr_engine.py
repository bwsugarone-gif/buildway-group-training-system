# -*- coding: utf-8 -*-
"""
core/ocr/ocr_engine.py
Buildway AI Core — OCR layer for scanned PDFs and image files.

Local OCR only. No cloud OCR, no background queue.
Requires: pypdf, Pillow, pytesseract (optional), pdf2image (optional)
"""

import tempfile
from pathlib import Path
from typing import Any

import pypdf
from PIL import Image


MAX_OCR_PDF_PAGES = 20
OCR_UNAVAILABLE_MESSAGE = "OCR is unavailable. Please provide a text-selectable PDF."
OCR_FAILED_MESSAGE = "OCR extraction failed. Please provide a clearer document."
OCR_SUCCESS_MESSAGE = "OCR extraction successful"
OCR_LARGE_PDF_MESSAGE = f"Large scanned PDF: only first {MAX_OCR_PDF_PAGES} pages processed."
OCR_PHASE_MESSAGE = "This document may be a scanned PDF. OCR support available."


def _base_result(file_path: Path, file_type: str) -> dict[str, Any]:
    return {
        "file_path": str(file_path),
        "file_type": file_type,
        "extracted_text": "",
        "selectable_text": "",
        "ocr_used": False,
        "ocr_page_count": 0,
        "ocr_status": "NOT_ATTEMPTED",
        "ocr_message": "",
        "page_count": 0,
        "is_scanned_pdf": False,
        "warning": "",
    }


def _normalise_text(text: str) -> str:
    return "\n".join(line.strip() for line in str(text or "").splitlines() if line.strip())


def extract_selectable_pdf_text(file_path: Path, max_pages: int | None = None) -> tuple[str, int]:
    """Extract selectable text from a PDF using pypdf."""
    reader = pypdf.PdfReader(str(file_path))
    page_count = len(reader.pages)
    limit = min(page_count, max_pages) if max_pages else page_count
    parts = []
    for idx, page in enumerate(reader.pages[:limit], 1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"[Page {idx}]\n{text.strip()}")
    return "\n\n".join(parts), page_count


def _tesseract_available() -> tuple[bool, str]:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True, ""
    except Exception as e:
        return False, str(e)


def _pdf2image_available() -> bool:
    try:
        import pdf2image  # noqa: F401
        return True
    except ImportError:
        return False


def _ocr_image(image: Image.Image, lang: str = "chi_tra+eng") -> str:
    """Run Tesseract OCR on a PIL Image."""
    import pytesseract
    return pytesseract.image_to_string(image, lang=lang)


def extract_text_with_ocr(file_path: Path, lang: str = "chi_tra+eng") -> dict[str, Any]:
    """
    Main entry point. Extracts text from PDF or image file.
    Falls back to OCR if selectable text is insufficient.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    result = _base_result(file_path, suffix)

    # ── Image files ───────────────────────────────────────────────────────────
    if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
        tess_ok, tess_err = _tesseract_available()
        if not tess_ok:
            result["ocr_status"] = "UNAVAILABLE"
            result["ocr_message"] = OCR_UNAVAILABLE_MESSAGE
            result["warning"] = tess_err
            return result
        try:
            img = Image.open(file_path)
            text = _normalise_text(_ocr_image(img, lang=lang))
            result["extracted_text"] = text
            result["ocr_used"] = True
            result["ocr_page_count"] = 1
            result["ocr_status"] = "SUCCESS" if text else "EMPTY"
            result["ocr_message"] = OCR_SUCCESS_MESSAGE if text else OCR_FAILED_MESSAGE
        except Exception as e:
            result["ocr_status"] = "FAILED"
            result["ocr_message"] = OCR_FAILED_MESSAGE
            result["warning"] = str(e)
        return result

    # ── PDF files ─────────────────────────────────────────────────────────────
    if suffix == ".pdf":
        selectable, page_count = extract_selectable_pdf_text(file_path)
        result["selectable_text"] = selectable
        result["page_count"] = page_count

        # Enough selectable text — no OCR needed
        if len(selectable.strip()) >= 100:
            result["extracted_text"] = selectable
            result["ocr_status"] = "SKIPPED_SELECTABLE"
            result["ocr_message"] = "Selectable text found; OCR not required."
            return result

        # Scanned PDF — attempt OCR
        result["is_scanned_pdf"] = True
        tess_ok, tess_err = _tesseract_available()
        p2i_ok = _pdf2image_available()

        if not tess_ok or not p2i_ok:
            result["ocr_status"] = "UNAVAILABLE"
            result["ocr_message"] = OCR_PHASE_MESSAGE
            result["warning"] = tess_err or "pdf2image not installed"
            result["extracted_text"] = selectable
            return result

        try:
            from pdf2image import convert_from_path

            if page_count > MAX_OCR_PDF_PAGES:
                result["warning"] = OCR_LARGE_PDF_MESSAGE

            with tempfile.TemporaryDirectory() as tmp:
                images = convert_from_path(
                    str(file_path),
                    dpi=200,
                    first_page=1,
                    last_page=min(page_count, MAX_OCR_PDF_PAGES),
                    output_folder=tmp,
                )
                parts = []
                for idx, img in enumerate(images, 1):
                    text = _normalise_text(_ocr_image(img, lang=lang))
                    if text:
                        parts.append(f"[Page {idx}]\n{text}")

            ocr_text = "\n\n".join(parts)
            result["extracted_text"] = ocr_text or selectable
            result["ocr_used"] = True
            result["ocr_page_count"] = len(images)
            result["ocr_status"] = "SUCCESS" if ocr_text else "EMPTY"
            result["ocr_message"] = OCR_SUCCESS_MESSAGE if ocr_text else OCR_FAILED_MESSAGE
        except Exception as e:
            result["ocr_status"] = "FAILED"
            result["ocr_message"] = OCR_FAILED_MESSAGE
            result["warning"] = str(e)
            result["extracted_text"] = selectable
        return result

    # ── Unsupported ───────────────────────────────────────────────────────────
    result["ocr_status"] = "UNSUPPORTED"
    result["ocr_message"] = f"Unsupported file type: {suffix}"
    return result
