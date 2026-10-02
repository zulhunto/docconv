"""EPUB book converter using ebooklib and HTML conversion."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from bs4 import BeautifulSoup
import markdownify

from docconv.assets import AssetManager
from docconv.converters.base import BaseConverter
from docconv.models import Asset, ConvertContext, DocMetadata, MarkdownResult
from docconv.registry import register

logger = logging.getLogger(__name__)


@register
class EpubConverter(BaseConverter):
    """Converts EPUB electronic books to Markdown chapter by chapter."""

    extensions: ClassVar[tuple[str, ...]] = (".epub",)

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        warnings: list[str] = []
        assets: list[Asset] = []

        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            return MarkdownResult.from_error(
                "ebooklib is required to convert EPUB files. Install with: pip install ebooklib"
            )

        try:
            book = epub.read_epub(str(path))
        except Exception as exc:
            return MarkdownResult.from_error(f"Cannot read EPUB: {exc}")

        # Metadata
        title_meta = book.get_metadata("DC", "title")
        title = title_meta[0][0] if title_meta else path.stem.replace("_", " ").title()

        creator_meta = book.get_metadata("DC", "creator")
        author = creator_meta[0][0] if creator_meta else ""

        lang_meta = book.get_metadata("DC", "language")
        language = lang_meta[0][0] if lang_meta else ""

        metadata = DocMetadata(
            title=title,
            author=author,
            source_format="EPUB",
            extra={"language": language} if language else {},
        )

        # Asset extraction (embedded images)
        if ctx.extract_images:
            asset_mgr = AssetManager(ctx.assets_dir, min_size_px=ctx.config.images.min_size_px)
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    try:
                        img_name = Path(item.get_name()).name
                        asset = asset_mgr.save_image_bytes(item.get_content(), hint_name=img_name)
                        if asset:
                            assets.append(asset)
                    except Exception as exc:
                        logger.debug("Failed to extract EPUB image: %s", exc)

        # Chapters
        chapters_md: list[str] = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content()
                soup = BeautifulSoup(content, "lxml")

                # Remove scripts/styles
                for tag in soup(["script", "style"]):
                    tag.decompose()

                chapter_text = markdownify.markdownify(
                    str(soup.body or soup),
                    heading_style="ATX",
                ).strip()

                if chapter_text:
                    chapters_md.append(chapter_text)

        full_md = f"# {title}\n\n" + "\n\n---\n\n".join(chapters_md) + "\n"
        return MarkdownResult(
            markdown=full_md,
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )
