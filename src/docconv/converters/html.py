"""HTML document converter using BeautifulSoup, lxml, and markdownify."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from bs4 import BeautifulSoup
import markdownify

from docconv.assets import AssetManager
from docconv.converters.base import BaseConverter
from docconv.models import Asset, ConvertContext, DocMetadata, MarkdownResult
from docconv.postprocess.tables import TableCell, render_structured_table
from docconv.registry import register

logger = logging.getLogger(__name__)


@register
class HtmlConverter(BaseConverter):
    """Converts HTML files to clean Markdown."""

    extensions: ClassVar[tuple[str, ...]] = (".html", ".htm", ".xhtml")

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        warnings: list[str] = []
        assets: list[Asset] = []

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return MarkdownResult.from_error(f"Cannot read HTML file: {exc}")

        soup = BeautifulSoup(content, "lxml")

        # Extract title & metadata
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            title = path.stem.replace("_", " ").title()

        author = ""
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            author = str(meta_author["content"]).strip()

        metadata = DocMetadata(
            title=title,
            author=author,
            source_format="HTML",
        )

        # Remove unnecessary elements
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        # Handle tables with colspan/rowspan
        if ctx.config.tables.fallback_html_on_merged_cells:
            for tbl in soup.find_all("table"):
                has_merged = bool(tbl.find(lambda t: t.has_attr("colspan") or t.has_attr("rowspan")))
                if has_merged:
                    # Keep as clean HTML or render via structured table
                    grid = self._parse_html_table(tbl)
                    table_md = render_structured_table(grid, fallback_html_on_merged=True)
                    # Replace in soup with placeholder or formatted text
                    tbl.replace_with(soup.new_string(f"\n\n{table_md}\n\n"))

        # Convert remaining HTML to Markdown
        md_text = markdownify.markdownify(
            str(soup.body or soup),
            heading_style="ATX",
            strip=["script", "style"],
        )

        return MarkdownResult(
            markdown=md_text.strip() + "\n",
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )

    def _parse_html_table(self, table_tag) -> list[list[TableCell]]:
        grid: list[list[TableCell]] = []
        for tr in table_tag.find_all("tr"):
            row: list[TableCell] = []
            for cell in tr.find_all(["th", "td"]):
                colspan = int(cell.get("colspan", 1))
                rowspan = int(cell.get("rowspan", 1))
                is_header = cell.name == "th"
                row.append(
                    TableCell(
                        text=cell.get_text(separator=" ", strip=True),
                        rowspan=rowspan,
                        colspan=colspan,
                        is_header=is_header,
                    )
                )
            if row:
                grid.append(row)
        return grid
