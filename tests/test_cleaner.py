"""Tests for postprocessing: cleaner, dehyphenation, and tables."""

from docconv.postprocess.cleaner import clean_markdown, clean_whitespace, dehyphenate, strip_headers_and_footers
from docconv.postprocess.tables import TableCell, render_html_table, render_pipe_table, render_structured_table


def test_dehyphenation():
    # Word broken with hyphen across newline where next line starts lowercase
    sample = "Pemerintah sedang meren-\ncanakan pembangunan infrastruktur."
    cleaned = dehyphenate(sample)
    assert "merencanakan" in cleaned
    assert "meren-\ncanakan" not in cleaned

    # Hyphenated compound word where next line starts with uppercase or list item should remain
    preserve = "Sosial-\nEkonomi"
    assert "Sosial-\nEkonomi" == dehyphenate(preserve)

    # Protect code blocks
    code = "```python\nfoo-\nbar\n```"
    assert dehyphenate(code) == code


def test_clean_whitespace():
    raw = "Paragraf 1.   \n\n\n\nParagraf 2."
    cleaned = clean_whitespace(raw, max_blank_lines=1)
    assert "\n\n\n" not in cleaned
    assert "Paragraf 1.\n\nParagraf 2." in cleaned


def test_strip_headers_and_footers():
    pages_text = (
        "Laporan Tahunan 2026\nIsi halaman satu.\nHal. 1\n"
        "\n---\n\n"
        "Laporan Tahunan 2026\nIsi halaman dua.\nHal. 2\n"
        "\n---\n\n"
        "Laporan Tahunan 2026\nIsi halaman tiga.\nHal. 3\n"
    )
    cleaned = strip_headers_and_footers(pages_text)
    # Recurring header should be removed
    assert cleaned.count("Laporan Tahunan 2026") == 0
    # Page numbers should be stripped
    assert "Hal. 1" not in cleaned
    assert "Hal. 2" not in cleaned


def test_render_pipe_table():
    rows = [["ID", "Name"], ["1", "Alice"], ["2", "Bob"]]
    res = render_pipe_table(rows)
    assert "| ID" in res
    assert "| ---" in res
    assert "| Alice" in res


def test_render_structured_table_merged_fallback():
    # Cell with colspan > 1 triggers HTML table
    cells = [
        [TableCell(text="Group Header", colspan=2, is_header=True)],
        [TableCell(text="A"), TableCell(text="B")],
    ]
    res = render_structured_table(cells, fallback_html_on_merged=True)
    assert "<table" in res
    assert 'colspan="2"' in res
