"""Optional Docling PDF converter engine for complex layout documents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from docconv.converters.base import BaseConverter
from docconv.models import ConvertContext, DocMetadata, MarkdownResult

logger = logging.getLogger(__name__)


class DoclingPdfConverter(BaseConverter):
    """Converts complex PDFs using the Docling engine."""

    extensions: ClassVar[tuple[str, ...]] = (".pdf",)

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            return MarkdownResult.from_error(
                "Docling engine requested but 'docling' is not installed. "
                "Install with: pip install docconv[docling]"
            )

        try:
            converter = DocumentConverter()
            conversion_res = converter.convert(str(path))
            md_content = conversion_res.document.export_to_markdown()

            metadata = DocMetadata(
                title=path.stem.replace("_", " ").title(),
                source_format="PDF (Docling)",
            )

            return MarkdownResult(markdown=md_content, metadata=metadata)
        except Exception as exc:
            logger.error("Docling conversion failed for %s: %s", path, exc)
            return MarkdownResult.from_error(f"Docling error: {exc}")
