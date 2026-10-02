"""Postprocessing modules: cleaner, tables, frontmatter."""

from docconv.postprocess.cleaner import clean_markdown, dehyphenate, strip_headers_and_footers
from docconv.postprocess.frontmatter import format_frontmatter
from docconv.postprocess.tables import (
    TableCell,
    render_html_table,
    render_pipe_table,
    render_structured_table,
)

__all__ = [
    "clean_markdown",
    "dehyphenate",
    "strip_headers_and_footers",
    "format_frontmatter",
    "TableCell",
    "render_html_table",
    "render_pipe_table",
    "render_structured_table",
]
