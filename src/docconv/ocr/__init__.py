"""OCR subsystem: detection and engines."""

from docconv.ocr.detect import get_scanned_pages, is_pdf_page_scanned
from docconv.ocr.engine import (
    is_ocrmypdf_available,
    is_tesseract_available,
    ocr_image,
    preprocess_image_for_ocr,
    run_ocrmypdf_on_file,
)

__all__ = [
    "get_scanned_pages",
    "is_pdf_page_scanned",
    "is_ocrmypdf_available",
    "is_tesseract_available",
    "ocr_image",
    "preprocess_image_for_ocr",
    "run_ocrmypdf_on_file",
]
