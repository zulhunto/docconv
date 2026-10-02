"""Image-to-Markdown converter using pytesseract OCR."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from PIL import Image

from docconv.assets import AssetManager
from docconv.converters.base import BaseConverter
from docconv.models import Asset, ConvertContext, DocMetadata, MarkdownResult
from docconv.ocr.engine import is_tesseract_available, ocr_image
from docconv.registry import register

logger = logging.getLogger(__name__)


@register
class ImageConverter(BaseConverter):
    """Converts images containing text to Markdown via OCR."""

    extensions: ClassVar[tuple[str, ...]] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".tif",
        ".webp",
        ".bmp",
    )

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        warnings: list[str] = []
        assets: list[Asset] = []

        try:
            img = Image.open(path)
            width, height = img.size
        except Exception as exc:
            return MarkdownResult.from_error(f"Cannot open image file: {exc}")

        title = path.stem.replace("_", " ").title()
        metadata = DocMetadata(
            title=title,
            source_format=f"Image ({img.format or 'Unknown'})",
            extra={"width": width, "height": height},
        )

        # Save copy to assets if image extraction enabled
        if ctx.extract_images:
            asset_mgr = AssetManager(ctx.assets_dir, min_size_px=ctx.config.images.min_size_px)
            asset = asset_mgr.save_file(path)
            if asset:
                assets.append(asset)

        # Run OCR
        if not is_tesseract_available():
            warnings.append("Tesseract is not installed; unable to perform OCR on image.")
            img_ref = f"![{title}]({path.name})" if not assets else assets[0].markdown_ref
            md = f"# {title}\n\n{img_ref}\n\n*(OCR unavailable)*\n"
            return MarkdownResult(markdown=md, metadata=metadata, assets=assets, warnings=warnings)

        try:
            ocr_text = ocr_image(img, lang=ctx.ocr_lang, preprocess=True)
        except Exception as exc:
            warnings.append(f"OCR failed: {exc}")
            ocr_text = ""

        # Build markdown output
        img_ref = assets[0].markdown_ref if assets else f"![{title}]({path.name})"
        md_parts = [f"# {title}", "", img_ref, ""]
        if ocr_text:
            md_parts.extend(["## Extracted Text", "", ocr_text])
        else:
            md_parts.append("*(No text detected)*")

        return MarkdownResult(
            markdown="\n".join(md_parts) + "\n",
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )
