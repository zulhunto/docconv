"""Tests for quality measurement module."""

from docconv.quality import count_markdown_metrics, evaluate_quality
from tests.make_fixtures import DATA_DIR, generate_all_fixtures


def test_count_markdown_metrics():
    sample_md = """# Title 1
## Section 2

Here is a paragraph with [a link](https://example.com) and an image ![Alt](img.png).

| Col 1 | Col 2 |
| ----- | ----- |
| Val 1 | Val 2 |
"""
    metrics = count_markdown_metrics(sample_md)
    assert metrics.headings == 2
    assert metrics.tables == 1
    assert metrics.images == 1
    assert metrics.links == 1
    assert metrics.words > 10


def test_evaluate_quality_on_text():
    generate_all_fixtures()
    src = DATA_DIR / "sample.txt"
    md_content = "# Sample\n\nCatatan Rapat Strategi 2026\n1. Pendahuluan rencana transformasi digital."
    report = evaluate_quality(src, md_content)

    assert report.source_metrics.words > 0
    assert report.md_metrics.headings == 1
    assert "words" in report.retention_rates
