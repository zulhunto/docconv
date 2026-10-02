"""Quality evaluation: compare structural metrics between source document and converted Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class DocMetrics:
    """Document structural metrics."""

    headings: int = 0
    tables: int = 0
    images: int = 0
    links: int = 0
    words: int = 0


@dataclass
class QualityReport:
    """Comparison report between source and converted Markdown."""

    source_path: Path
    source_metrics: DocMetrics
    md_metrics: DocMetrics

    @property
    def differences(self) -> dict[str, int]:
        s = asdict(self.source_metrics)
        m = asdict(self.md_metrics)
        return {k: m[k] - s[k] for k in s}

    @property
    def retention_rates(self) -> dict[str, float]:
        rates = {}
        s = asdict(self.source_metrics)
        m = asdict(self.md_metrics)
        for k, src_val in s.items():
            if src_val == 0:
                rates[k] = 100.0 if m[k] == 0 else 100.0
            else:
                rates[k] = min(100.0, round((m[k] / src_val) * 100.0, 1))
        return rates


def count_markdown_metrics(markdown: str) -> DocMetrics:
    """Extract structural metrics from Markdown text."""
    # Headings: lines starting with #
    headings = len(re.findall(r"^#{1,6}\s+\S+", markdown, re.MULTILINE))

    # Tables: GFM pipe separator rows (| --- |) or <table> tags
    pipe_tables = len(re.findall(r"^\|?\s*[-:]+[-| :]*\|?\s*$", markdown, re.MULTILINE))
    html_tables = len(re.findall(r"<table\b", markdown, re.IGNORECASE))
    tables = pipe_tables + html_tables

    # Images: ![alt](url) or <img ...>
    md_images = len(re.findall(r"!\[.*?\]\(.*?\)", markdown))
    html_images = len(re.findall(r"<img\b", markdown, re.IGNORECASE))
    images = md_images + html_images

    # Links: [text](url) not preceded by !
    md_links = len(re.findall(r"(?<!!)\[.*?\]\(.*?\)", markdown))
    html_links = len(re.findall(r"<a\s+[^>]*href=", markdown, re.IGNORECASE))
    links = md_links + html_links

    # Words
    words = len(re.findall(r"\b\w+\b", markdown))

    return DocMetrics(
        headings=headings,
        tables=tables,
        images=images,
        links=links,
        words=words,
    )


def count_source_metrics(path: Path) -> DocMetrics:
    """Count structural metrics in source document (exact for DOCX/PPTX/HTML, heuristic for PDF)."""
    ext = path.suffix.lower()

    if ext == ".docx":
        return _count_docx(path)
    if ext == ".pptx":
        return _count_pptx(path)
    if ext in (".html", ".htm"):
        return _count_html(path)
    if ext == ".pdf":
        return _count_pdf(path)

    # Fallback: simple text count
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
        words = len(re.findall(r"\b\w+\b", txt))
        return DocMetrics(words=words)
    except Exception:
        return DocMetrics()


def _count_docx(path: Path) -> DocMetrics:
    try:
        import docx

        doc = docx.Document(path)
        headings = 0
        words = 0
        for p in doc.paragraphs:
            style = (p.style.name or "").lower()
            if style.startswith("heading") or style in ("title", "subtitle"):
                headings += 1
            words += len(re.findall(r"\b\w+\b", p.text))

        tables = len(doc.tables)
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    words += len(re.findall(r"\b\w+\b", cell.text))

        # Images
        import zipfile

        images = 0
        with zipfile.ZipFile(path, "r") as zf:
            images = sum(1 for n in zf.namelist() if n.startswith("word/media/"))

        return DocMetrics(headings=headings, tables=tables, images=images, words=words)
    except Exception:
        return DocMetrics()


def _count_pptx(path: Path) -> DocMetrics:
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        prs = Presentation(path)
        headings = 0
        tables = 0
        images = 0
        words = 0

        for slide in prs.slides:
            if slide.shapes.title and slide.shapes.title.text.strip():
                headings += 1
            for shape in slide.shapes:
                if shape.has_text_frame:
                    words += len(re.findall(r"\b\w+\b", shape.text_frame.text))
                if shape.has_table:
                    tables += 1
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    images += 1

        return DocMetrics(headings=headings, tables=tables, images=images, words=words)
    except Exception:
        return DocMetrics()


def _count_html(path: Path) -> DocMetrics:
    try:
        from bs4 import BeautifulSoup

        content = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(content, "lxml")
        headings = len(soup.find_all(re.compile(r"^h[1-6]$")))
        tables = len(soup.find_all("table"))
        images = len(soup.find_all("img"))
        links = len(soup.find_all("a", href=True))
        words = len(re.findall(r"\b\w+\b", soup.get_text()))
        return DocMetrics(headings=headings, tables=tables, images=images, links=links, words=words)
    except Exception:
        return DocMetrics()


def _count_pdf(path: Path) -> DocMetrics:
    try:
        import pymupdf as fitz

        doc = fitz.open(path)
        images = 0
        words = 0
        tables = 0
        headings = 0

        for page in doc:
            images += len(page.get_images())
            text = page.get_text()
            words += len(re.findall(r"\b\w+\b", text))
            # Heuristic heading count: lines in page starting with capital or numbering followed by short text
            for line in text.splitlines():
                line_s = line.strip()
                if 3 < len(line_s) < 80 and not line_s.endswith((".", ",", ";")):
                    if re.match(r"^(\d+(\.\d+)*|[A-Z][a-zA-Z\s]{2,})", line_s):
                        headings += 1
            # Count tables if PyMuPDF table finder is available
            try:
                tabs = page.find_tables()
                tables += len(tabs.tables)
            except Exception:
                pass

        doc.close()
        return DocMetrics(headings=headings, tables=tables, images=images, words=words)
    except Exception:
        return DocMetrics()


def evaluate_quality(source_path: Path, markdown_path_or_content: Path | str) -> QualityReport:
    """Generate a quality comparison report between source file and converted markdown."""
    src_metrics = count_source_metrics(source_path)
    if isinstance(markdown_path_or_content, Path):
        md_text = markdown_path_or_content.read_text(encoding="utf-8", errors="replace")
    else:
        md_text = markdown_path_or_content

    md_metrics = count_markdown_metrics(md_text)
    return QualityReport(source_path=source_path, source_metrics=src_metrics, md_metrics=md_metrics)
