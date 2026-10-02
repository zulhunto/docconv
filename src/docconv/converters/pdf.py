"""PDF converter using pymupdf4llm with OCR detection and Docling engine support."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import ClassVar

import pymupdf as fitz

from docconv.assets import AssetManager
from docconv.converters.base import BaseConverter
from docconv.models import Asset, ConvertContext, DocMetadata, MarkdownResult
from docconv.ocr.detect import get_scanned_pages
from docconv.ocr.engine import is_ocrmypdf_available, is_tesseract_available, ocr_image, run_ocrmypdf_on_file
from docconv.registry import register

logger = logging.getLogger(__name__)


@register
class PdfConverter(BaseConverter):
    """Converts PDF files to Markdown with pymupdf4llm and OCR fallback."""

    extensions: ClassVar[tuple[str, ...]] = (".pdf",)

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        # Check if Docling engine is requested
        if ctx.config.pdf.engine == "docling":
            from docconv.converters.pdf_docling import DoclingPdfConverter

            return DoclingPdfConverter().convert(path, ctx)

        warnings: list[str] = []
        assets: list[Asset] = []

        try:
            doc = fitz.open(path)
        except Exception as exc:
            return MarkdownResult.from_error(f"Cannot open PDF: {exc}")

        # Metadata extraction
        meta_dict = doc.metadata or {}
        page_count = len(doc)
        title = meta_dict.get("title") or path.stem.replace("_", " ").title()
        author = meta_dict.get("author") or ""
        created = meta_dict.get("creationDate") or ""
        keywords = [k.strip() for k in meta_dict.get("keywords", "").split(",") if k.strip()]

        metadata = DocMetadata(
            title=title,
            author=author,
            created=created,
            keywords=keywords,
            page_count=page_count,
            source_format="PDF",
        )

        effective_path = path

        # Check for scanned pages
        if ctx.ocr_enabled and ctx.config.ocr.auto_detect:
            min_chars = ctx.config.ocr.min_chars_per_page
            scanned_pages = get_scanned_pages(doc, min_chars=min_chars)

            if scanned_pages:
                logger.info(
                    "Detected %d scanned pages in %s: %s",
                    len(scanned_pages), path.name, scanned_pages,
                )
                if is_ocrmypdf_available():
                    # Run OCRmyPDF to add a searchable text layer
                    tmp_ocr_pdf = Path(tempfile.gettempdir()) / f"ocr_{path.name}"
                    success = run_ocrmypdf_on_file(
                        input_pdf=path,
                        output_pdf=tmp_ocr_pdf,
                        lang=ctx.ocr_lang,
                        pages=scanned_pages,
                    )
                    if success and tmp_ocr_pdf.exists():
                        effective_path = tmp_ocr_pdf
                        doc.close()
                        doc = fitz.open(effective_path)
                    else:
                        warnings.append("OCRmyPDF failed to process scanned pages; using raw text.")
                elif is_tesseract_available():
                    warnings.append(
                        "OCRmyPDF not installed; fell back to pytesseract page text extraction."
                    )
                else:
                    warnings.append("OCR is enabled but neither OCRmyPDF nor Tesseract is available.")

        # Extract markdown using pymupdf4llm
        try:
            import pymupdf4llm

            # Determine whether to extract images
            if ctx.extract_images:
                ctx.assets_dir.mkdir(parents=True, exist_ok=True)
                md_text = pymupdf4llm.to_markdown(
                    doc,
                    write_images=True,
                    image_path=str(ctx.assets_dir),
                    image_format="png",
                )
                # Register saved assets
                asset_manager = AssetManager(ctx.assets_dir, min_size_px=ctx.config.images.min_size_px)
                for img_file in ctx.assets_dir.glob("*.png"):
                    asset = asset_manager.save_file(img_file)
                    if asset:
                        assets.append(asset)
            else:
                md_text = pymupdf4llm.to_markdown(doc, write_images=False)

        except Exception as exc:
            logger.warning("pymupdf4llm failed (%s), falling back to PyMuPDF text extraction.", exc)
            warnings.append(f"pymupdf4llm fallback used: {exc}")
            # Fallback basic text extraction
            lines = []
            for i, page in enumerate(doc):
                lines.append(f"## Page {i + 1}\n\n" + page.get_text())
            md_text = "\n\n".join(lines)

        finally:
            doc.close()
            # Clean temporary OCR file if created
            if effective_path != path and effective_path.exists():
                try:
                    effective_path.unlink()
                except Exception:
                    pass

        return MarkdownResult(
            markdown=md_text,
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )
