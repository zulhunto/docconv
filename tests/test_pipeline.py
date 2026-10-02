"""Tests for ConversionPipeline: batch recursive, frontmatter prepending, error isolation."""

from pathlib import Path
from docconv.config import AppConfig
from docconv.pipeline import ConversionPipeline
from tests.make_fixtures import DATA_DIR, generate_all_fixtures


def test_pipeline_convert_single_file(tmp_path):
    generate_all_fixtures()
    cfg = AppConfig(output_dir=tmp_path)
    cfg.ocr.enabled = False
    pipeline = ConversionPipeline(cfg)

    src = DATA_DIR / "sample.txt"
    item_res = pipeline.convert_file(src)

    assert item_res.success
    assert item_res.output_path is not None
    assert item_res.output_path.exists()

    content = item_res.output_path.read_text(encoding="utf-8")
    assert content.startswith("---")  # Front matter YAML
    assert "title: Sample" in content or "title:" in content
    assert "Catatan Rapat" in content


def test_pipeline_batch_directory_and_error_isolation(tmp_path):
    generate_all_fixtures()

    # Create dummy corrupt file in input dir
    test_batch_dir = tmp_path / "batch_in"
    test_batch_dir.mkdir()

    # Copy some fixtures
    (test_batch_dir / "valid.txt").write_text("Valid text content", encoding="utf-8")
    (test_batch_dir / "valid.json").write_text('{"name": "test"}', encoding="utf-8")
    # Corrupt PDF file
    (test_batch_dir / "corrupted.pdf").write_bytes(b"NOT A REAL PDF FILE")

    out_dir = tmp_path / "batch_out"
    cfg = AppConfig(output_dir=out_dir)
    cfg.ocr.enabled = False
    cfg.batch.continue_on_error = True

    pipeline = ConversionPipeline(cfg)
    summary = pipeline.convert_path(test_batch_dir, output_dir=out_dir)

    assert summary.total == 3
    assert summary.succeeded == 2
    assert summary.failed == 1
    assert (out_dir / "valid.md").exists()
    assert (out_dir / "valid.md").exists()
