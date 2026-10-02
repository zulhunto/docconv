"""DOCX to Markdown converter with heading, table, image, and footnote support."""

from __future__ import annotations

import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import ClassVar

import docx
from docx.document import Document as _DocumentClass
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from docconv.assets import AssetManager
from docconv.converters.base import BaseConverter
from docconv.models import Asset, ConvertContext, DocMetadata, MarkdownResult
from docconv.postprocess.tables import TableCell, render_structured_table
from docconv.registry import register

logger = logging.getLogger(__name__)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@register
class DocxConverter(BaseConverter):
    """Converts Microsoft Word (.docx) files to Markdown."""

    extensions: ClassVar[tuple[str, ...]] = (".docx",)

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        warnings: list[str] = []
        assets: list[Asset] = []

        try:
            doc = docx.Document(path)
        except Exception as exc:
            return MarkdownResult.from_error(f"Cannot open DOCX: {exc}")

        # 1. Metadata
        metadata = self._extract_metadata(doc, path)

        # 2. Extract embedded images from zip
        if ctx.extract_images:
            assets = self._extract_images_from_zip(path, ctx)

        # 3. Extract footnotes from word/footnotes.xml
        footnotes = self._extract_footnotes(path)

        # 4. Parse document body in sequence (paragraphs & tables)
        body_parts: list[str] = []
        for child in doc.element.body:
            if isinstance(child, CT_P):
                p = Paragraph(child, doc)
                p_text = self._convert_paragraph(p, footnotes)
                if p_text:
                    body_parts.append(p_text)
            elif isinstance(child, CT_Tbl):
                tbl = Table(child, doc)
                tbl_text = self._convert_table(tbl, ctx.config.tables.fallback_html_on_merged_cells)
                if tbl_text:
                    body_parts.append(tbl_text)

        # 5. Append footnotes section if any footnotes are referenced
        if footnotes:
            body_parts.append("\n---\n")
            for fn_id, fn_text in sorted(footnotes.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
                if int(fn_id) > 0:  # Skip separator / continuation footnotes (id <= 0)
                    body_parts.append(f"[^{fn_id}]: {fn_text}")

        full_md = "\n\n".join(body_parts) + "\n"
        return MarkdownResult(
            markdown=full_md,
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )

    def _extract_metadata(self, doc: _DocumentClass, path: Path) -> DocMetadata:
        cp = doc.core_properties
        title = cp.title or path.stem.replace("_", " ").title()
        author = cp.author or ""
        created = cp.created.isoformat() if cp.created else ""
        modified = cp.modified.isoformat() if cp.modified else ""
        subject = cp.subject or ""
        keywords = [k.strip() for k in (cp.keywords or "").split(",") if k.strip()]

        return DocMetadata(
            title=title,
            author=author,
            created=created,
            modified=modified,
            subject=subject,
            keywords=keywords,
            source_format="DOCX",
        )

    def _extract_images_from_zip(self, path: Path, ctx: ConvertContext) -> list[Asset]:
        assets: list[Asset] = []
        asset_mgr = AssetManager(ctx.assets_dir, min_size_px=ctx.config.images.min_size_px)

        try:
            with zipfile.ZipFile(path, "r") as zf:
                for filename in zf.namelist():
                    if filename.startswith("word/media/"):
                        data = zf.read(filename)
                        img_name = Path(filename).name
                        asset = asset_mgr.save_image_bytes(data, hint_name=img_name)
                        if asset:
                            assets.append(asset)
        except Exception as exc:
            logger.warning("Error extracting DOCX images: %s", exc)

        return assets

    def _extract_footnotes(self, path: Path) -> dict[str, str]:
        """Read word/footnotes.xml directly to extract footnote text by ID."""
        footnotes: dict[str, str] = {}
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if "word/footnotes.xml" not in zf.namelist():
                    return footnotes
                xml_data = zf.read("word/footnotes.xml")
                root = ET.fromstring(xml_data)
                for fn in root.findall(".//w:footnote", NS):
                    fn_id = fn.attrib.get(f"{{{NS['w']}}}id", "")
                    texts = [t.text for t in fn.findall(".//w:t", NS) if t.text]
                    joined_text = " ".join("".join(texts).split())
                    if joined_text and fn_id:
                        footnotes[fn_id] = joined_text
        except Exception as exc:
            logger.debug("No footnotes extracted or error reading footnotes.xml: %s", exc)
        return footnotes

    def _convert_paragraph(self, p: Paragraph, footnotes: dict[str, str]) -> str:
        text = p.text.strip()
        if not text:
            return ""

        style_name = (p.style.name or "").lower()

        # Heading detection
        if style_name.startswith("heading"):
            parts = style_name.split()
            level = 1
            if len(parts) > 1 and parts[1].isdigit():
                level = min(6, max(1, int(parts[1])))
            return f"{'#' * level} {text}"

        if style_name == "title":
            return f"# {text}"
        if style_name == "subtitle":
            return f"### {text}"

        # Build inline markdown (bold, italic, footnotes)
        run_parts: list[str] = []
        for r in p.runs:
            run_text = r.text
            if not run_text:
                continue
            if r.bold and r.italic:
                run_text = f"***{run_text}***"
            elif r.bold:
                run_text = f"**{run_text}**"
            elif r.italic:
                run_text = f"*{run_text}*"
            if r.font.strike:
                run_text = f"~~{run_text}~~"
            run_parts.append(run_text)

        p_line = "".join(run_parts).strip() if run_parts else text

        # Check for footnote reference in XML
        for fn_ref in p._p.findall(".//w:footnoteReference", NS):
            fn_id = fn_ref.attrib.get(f"{{{NS['w']}}}id")
            if fn_id and fn_id in footnotes and int(fn_id) > 0:
                p_line += f"[^{fn_id}]"

        # List items
        if "list" in style_name or "bullet" in style_name:
            return f"- {p_line}"
        if "number" in style_name:
            return f"1. {p_line}"

        return p_line

    def _convert_table(self, table: Table, fallback_html: bool = True) -> str:
        """Convert a docx Table into Markdown pipe table or HTML table."""
        if not table.rows:
            return ""

        grid: list[list[TableCell]] = []
        # Track seen cells for merged detection
        seen_cells: set[int] = set()

        for r_idx, row in enumerate(table.rows):
            grid_row: list[TableCell] = []
            for c_idx, cell in enumerate(row.cells):
                cell_id = id(cell._tc)
                if cell_id in seen_cells:
                    continue
                seen_cells.add(cell_id)

                # Check gridSpan (colspan)
                grid_span = 1
                grid_span_elem = cell._tc.find(f".//{{{NS['w']}}}gridSpan")
                if grid_span_elem is not None:
                    grid_span = int(grid_span_elem.attrib.get(f"{{{NS['w']}}}val", 1))

                # Check vMerge (rowspan)
                row_span = 1
                v_merge = cell._tc.find(f".//{{{NS['w']}}}vMerge")
                if v_merge is not None and v_merge.attrib.get(f"{{{NS['w']}}}val") == "restart":
                    # Calculate vertical span
                    for subsequent_row in table.rows[r_idx + 1:]:
                        if c_idx < len(subsequent_row.cells):
                            sub_cell = subsequent_row.cells[c_idx]
                            sub_v = sub_cell._tc.find(f".//{{{NS['w']}}}vMerge")
                            if sub_v is not None and sub_v.attrib.get(f"{{{NS['w']}}}val") is None:
                                row_span += 1
                                seen_cells.add(id(sub_cell._tc))
                            else:
                                break

                is_hdr = (r_idx == 0)
                grid_row.append(
                    TableCell(
                        text=cell.text.strip(),
                        rowspan=row_span,
                        colspan=grid_span,
                        is_header=is_hdr,
                    )
                )
            if grid_row:
                grid.append(grid_row)

        return render_structured_table(grid, fallback_html_on_merged=fallback_html)
