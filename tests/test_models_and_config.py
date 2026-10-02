"""Tests for models and configuration loading."""

from pathlib import Path
from docconv.config import AppConfig, load_config
from docconv.models import Asset, DocMetadata, MarkdownResult


def test_metadata_to_frontmatter():
    meta = DocMetadata(
        title="Sample Document",
        author="Alice",
        created="2026-01-01",
        keywords=["ai", "markdown"],
        page_count=5,
        source_format="DOCX",
    )
    fm = meta.to_frontmatter_dict()
    assert fm["title"] == "Sample Document"
    assert fm["author"] == "Alice"
    assert fm["pages"] == 5
    assert fm["keywords"] == ["ai", "markdown"]


def test_markdown_result_status():
    success_res = MarkdownResult(markdown="# Test")
    assert success_res.success is True
    assert success_res.error is None

    err_res = MarkdownResult.from_error("Failed to parse")
    assert err_res.success is False
    assert err_res.error == "Failed to parse"


def test_asset_markdown_ref():
    asset = Asset(
        original_name="logo.png",
        saved_path=Path("assets/logo.png"),
        mime_type="image/png",
    )
    assert "![" in asset.markdown_ref
    assert "logo.png" in asset.markdown_ref


def test_load_default_config():
    cfg = load_config(path=Path("non_existent_config.yaml"))
    assert isinstance(cfg, AppConfig)
    assert cfg.ocr.lang == "ind+eng"
    assert cfg.images.folder == "assets"
    assert cfg.batch.continue_on_error is True
