"""Table rendering utilities: GFM pipe tables vs HTML fallback for merged cells."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass
class TableCell:
    """Represents a table cell with optional row and column span."""

    text: str
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False


def clean_cell_text(text: str) -> str:
    """Clean text for inclusion in a pipe table cell."""
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("|", "\\|")


def render_pipe_table(rows: list[list[str]], has_header: bool = True) -> str:
    """Render a 2D list of strings as a standard GitHub Flavored Markdown table."""
    if not rows:
        return ""

    num_cols = max(len(row) for row in rows)
    if num_cols == 0:
        return ""

    # Normalize row lengths
    normalized_rows = []
    for row in rows:
        cleaned = [clean_cell_text(cell) for cell in row]
        if len(cleaned) < num_cols:
            cleaned.extend([""] * (num_cols - len(cleaned)))
        normalized_rows.append(cleaned)

    # Calculate column widths
    col_widths = [3] * num_cols
    for row in normalized_rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    lines: list[str] = []

    # Header
    header_cells = normalized_rows[0]
    header_line = "| " + " | ".join(
        cell.ljust(col_widths[i]) for i, cell in enumerate(header_cells)
    ) + " |"
    lines.append(header_line)

    separator_line = "| " + " | ".join(
        "-" * col_widths[i] for i in range(num_cols)
    ) + " |"
    lines.append(separator_line)

    # Body
    body_rows = normalized_rows[1:] if has_header else normalized_rows
    for row in body_rows:
        line = "| " + " | ".join(
            cell.ljust(col_widths[i]) for i, cell in enumerate(row)
        ) + " |"
        lines.append(line)

    return "\n".join(lines)


def render_html_table(rows: list[list[TableCell]]) -> str:
    """Render cells as standard HTML <table> preserving colspan and rowspan."""
    if not rows:
        return ""

    lines = ["<table>"]
    for row_idx, row in enumerate(rows):
        lines.append("  <tr>")
        for cell in row:
            tag = "th" if cell.is_header else "td"
            attrs = []
            if cell.colspan > 1:
                attrs.append(f'colspan="{cell.colspan}"')
            if cell.rowspan > 1:
                attrs.append(f'rowspan="{cell.rowspan}"')
            attr_str = (" " + " ".join(attrs)) if attrs else ""
            escaped_text = html.escape(cell.text.strip())
            escaped_text = escaped_text.replace("\n", "<br/>")
            lines.append(f"    <{tag}{attr_str}>{escaped_text}</{tag}>")
        lines.append("  </tr>")
    lines.append("</table>")
    return "\n".join(lines)


def render_structured_table(
    rows: list[list[TableCell]],
    fallback_html_on_merged: bool = True,
) -> str:
    """Render table rows.

    If any cell has rowspan > 1 or colspan > 1 and fallback_html_on_merged is True,
    generates an HTML table. Otherwise, renders a GFM pipe table.
    """
    has_merged = any(
        cell.rowspan > 1 or cell.colspan > 1
        for row in rows
        for cell in row
    )

    if has_merged and fallback_html_on_merged:
        return render_html_table(rows)

    # Simple pipe table representation
    simple_rows = [[cell.text for cell in row] for row in rows]
    has_header = any(cell.is_header for cell in (rows[0] if rows else []))
    return render_pipe_table(simple_rows, has_header=has_header)
