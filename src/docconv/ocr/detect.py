"""Detection of scanned / image-only pages in documents."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def is_pdf_page_scanned(page, min_chars: int = 25) -> bool:
    """Check if a PyMuPDF (fitz) page is scanned or text-poor.

    A page is considered scanned if:
    - Text character count (excluding whitespace) < min_chars, and
    - The page contains at least one embedded image or vector drawing.
    """
    try:
        text = page.get_text().strip()
        char_count = len(text)
        if char_count >= min_chars:
            return False

        # Page has very few chars; check if it has images
        images = page.get_images()
        if len(images) > 0:
            return True

        # If zero images and zero text, treat as blank or scanned
        return char_count < min_chars
    except Exception as exc:
        logger.warning("Error inspecting page for OCR: %s", exc)
        return False


def get_scanned_pages(doc, min_chars: int = 25) -> list[int]:
    """Return 0-indexed list of page numbers that need OCR in a PyMuPDF Document."""
    scanned: list[int] = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        if is_pdf_page_scanned(page, min_chars=min_chars):
            scanned.append(page_idx)
    return scanned
