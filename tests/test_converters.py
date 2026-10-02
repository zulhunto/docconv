"""Integration tests for all document converters using generated fixtures."""

import pytest
from pathlib import Path

from docconv.config import AppConfig
from docconv.models import ConvertContext
from docconv.registry import get_converter
from tests.make_fixtures import DATA_DIR, generate_all_fixtures


@pytest.fixture(scope="session", autouse=True)
def setup_fixtures():
    generate_all_fixtures()


@pytest.fixture
def convert_ctx(tmp_path):
    cfg = AppConfig()
    cfg.output_dir = tmp_path
    cfg.ocr.enabled = False  # Avoid requiring local tesseract binary during pure unit tests
    return ConvertContext(
        output_dir=tmp_path,
        assets_dir=tmp_path / "assets",
        config=cfg,
        ocr_enabled=False,
    )


def test_text_converter(convert_ctx):
    p = DATA_DIR / "sample.txt"
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "Catatan Rapat" in res.markdown
    assert res.metadata.source_format == "Text"


def test_json_converter(convert_ctx):
    p = DATA_DIR / "sample.json"
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "```json" in res.markdown
    assert "docconv" in res.markdown


def test_html_converter(convert_ctx):
    p = DATA_DIR / "sample.html"
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "# Pengantar docconv" in res.markdown or "Pengantar docconv" in res.markdown
    assert "Markdown" in res.markdown
    assert res.metadata.title == "Panduan Pengguna docconv"


def test_docx_converter(convert_ctx):
    p = DATA_DIR / "sample.docx"
    if not p.exists():
        pytest.skip("sample.docx fixture not present")
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "Judul Utama DOCX" in res.markdown
    assert "**tebal**" in res.markdown
    assert "*miring*" in res.markdown


def test_pptx_converter(convert_ctx):
    p = DATA_DIR / "sample.pptx"
    if not p.exists():
        pytest.skip("sample.pptx fixture not present")
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "Selamat Datang di docconv" in res.markdown


def test_xlsx_converter(convert_ctx):
    p = DATA_DIR / "sample.xlsx"
    if not p.exists():
        pytest.skip("sample.xlsx fixture not present")
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "Sheet: Ringkasan" in res.markdown
    assert "Laptop" in res.markdown


def test_csv_converter(convert_ctx):
    p = DATA_DIR / "sample.csv"
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "| Nama" in res.markdown
    assert "Engineering" in res.markdown


def test_pdf_converter(convert_ctx):
    p = DATA_DIR / "sample.pdf"
    if not p.exists():
        pytest.skip("sample.pdf fixture not present")
    conv = get_converter(p)
    assert conv is not None
    res = conv.convert(p, convert_ctx)
    assert res.success
    assert "Dokumen Uji PDF" in res.markdown or "pengujian konversi" in res.markdown
