"""OCR engines: OCRmyPDF for scanned PDFs and pytesseract with Pillow preprocessing for images."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageEnhance, ImageFilter

if TYPE_CHECKING:
    import ocrmypdf

logger = logging.getLogger(__name__)


def is_tesseract_available() -> bool:
    """Check if tesseract binary is available in PATH or pytesseract can locate it."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return shutil.which("tesseract") is not None


def is_ocrmypdf_available() -> bool:
    """Check if ocrmypdf library is available."""
    try:
        import ocrmypdf  # noqa: F401

        return True
    except ImportError:
        return False


def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """Lightweight preprocessing (grayscale, contrast enhancement, sharpening)."""
    # Convert to grayscale
    gray = img.convert("L")

    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(1.8)

    # Optional mild sharpening
    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    return sharpened


def ocr_image(
    image: Image.Image | Path,
    lang: str = "ind+eng",
    preprocess: bool = True,
) -> str:
    """Perform OCR on a PIL Image or image file path using pytesseract."""
    import pytesseract

    if isinstance(image, Path):
        img = Image.open(image)
    else:
        img = image

    if preprocess:
        img = preprocess_image_for_ocr(img)

    try:
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()
    except Exception as exc:
        logger.warning("pytesseract failed with lang '%s': %s. Retrying with default...", lang, exc)
        try:
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as inner_exc:
            logger.error("pytesseract OCR error: %s", inner_exc)
            raise


def run_ocrmypdf_on_file(
    input_pdf: Path,
    output_pdf: Path,
    lang: str = "ind+eng",
    pages: list[int] | None = None,
    redo_ocr: bool = False,
) -> bool:
    """Run OCRmyPDF to add a searchable text layer to scanned pages.

    Returns True if successful, False otherwise.
    """
    if not is_ocrmypdf_available():
        logger.warning("ocrmypdf is not installed. Scanned PDF cannot be OCR-layered.")
        return False

    import ocrmypdf

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    kwargs = {
        "input_file": input_pdf,
        "output_file": output_pdf,
        "language": lang.replace("+", "+"),
        "skip_text": not redo_ocr,
        "redo_ocr": redo_ocr,
        "progress_bar": False,
        "output_type": "pdf",
    }

    if pages:
        # OCRmyPDF accepts 1-indexed comma-separated string e.g. "1,2,5"
        pages_str = ",".join(str(p + 1) for p in sorted(set(pages)))
        kwargs["pages"] = pages_str

    try:
        exit_code = ocrmypdf.ocr(**kwargs)
        return exit_code == ocrmypdf.ExitCode.ok
    except Exception as exc:
        logger.warning("OCRmyPDF failed: %s", exc)
        return False
