"""Batch conversion pipeline with recursive folder traversal, error isolation, and postprocessing."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

# Ensure converters are registered
import docconv.converters  # noqa: F401
from docconv.config import AppConfig, load_config
from docconv.models import ConvertContext, MarkdownResult
from docconv.postprocess.cleaner import clean_markdown
from docconv.postprocess.frontmatter import format_frontmatter
from docconv.registry import get_converter, list_supported_extensions

logger = logging.getLogger(__name__)


@dataclass
class PipelineItemResult:
    """Result of converting a single file through the pipeline."""

    source_path: Path
    output_path: Path | None = None
    success: bool = False
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    assets_count: int = 0
    duration_seconds: float = 0.0


@dataclass
class PipelineSummary:
    """Summary of batch conversion."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    results: list[PipelineItemResult] = field(default_factory=list)

    def print_summary(self) -> None:
        logger.info(
            "Batch finished in %.2fs: %d total, %d succeeded, %d failed, %d skipped",
            self.duration_seconds,
            self.total,
            self.succeeded,
            self.failed,
            self.skipped,
        )


class ConversionPipeline:
    """Orchestrates conversion, postprocessing, file writing, and error isolation."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

    def convert_file(
        self,
        source: Path,
        output_file: Path | None = None,
        assets_dir: Path | None = None,
    ) -> PipelineItemResult:
        """Convert a single document file to Markdown."""
        start_t = time.perf_counter()
        source = source.resolve()

        if not source.exists():
            return PipelineItemResult(
                source_path=source,
                success=False,
                error=f"Source file does not exist: {source}",
            )

        converter = get_converter(source)
        if not converter:
            return PipelineItemResult(
                source_path=source,
                success=False,
                error=f"No converter found for extension {source.suffix}",
            )

        # Determine output file path
        if output_file is None:
            out_dir = self.config.output_dir.resolve()
            output_file = out_dir / f"{source.stem}.md"
        output_file = output_file.resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine assets directory
        if assets_dir is None:
            assets_dir = output_file.parent / self.config.images.folder
        assets_dir = assets_dir.resolve()

        # Build context
        ctx = ConvertContext(
            output_dir=output_file.parent,
            assets_dir=assets_dir,
            config=self.config,
            ocr_enabled=self.config.ocr.enabled,
            ocr_lang=self.config.ocr.lang,
            extract_images=self.config.images.extract,
            source_path=source,
        )

        # 1. Execute converter
        try:
            res: MarkdownResult = converter.convert(source, ctx)
        except Exception as exc:
            logger.exception("Converter exception on %s: %s", source, exc)
            return PipelineItemResult(
                source_path=source,
                success=False,
                error=f"Converter exception: {exc}",
                duration_seconds=time.perf_counter() - start_t,
            )

        if not res.success or res.error:
            return PipelineItemResult(
                source_path=source,
                success=False,
                error=res.error or "Unknown conversion error",
                warnings=res.warnings,
                duration_seconds=time.perf_counter() - start_t,
            )

        # 2. Postprocessing (cleaner)
        cleaned_md = clean_markdown(
            res.markdown,
            strip_headers_footers_flag=self.config.cleaning.strip_headers_footers,
            dehyphenate_flag=self.config.cleaning.dehyphenate,
            max_blank_lines=self.config.cleaning.max_blank_lines,
        )

        # 3. Prepend front matter YAML
        final_content = format_frontmatter(res.metadata, cleaned_md)

        # 4. Write output Markdown file
        try:
            output_file.write_text(final_content, encoding="utf-8")
        except Exception as exc:
            return PipelineItemResult(
                source_path=source,
                success=False,
                error=f"Failed to write output file: {exc}",
                warnings=res.warnings,
                duration_seconds=time.perf_counter() - start_t,
            )

        return PipelineItemResult(
            source_path=source,
            output_path=output_file,
            success=True,
            warnings=res.warnings,
            assets_count=len(res.assets),
            duration_seconds=time.perf_counter() - start_t,
        )

    def convert_path(
        self,
        input_path: Path,
        output_dir: Path | None = None,
    ) -> PipelineSummary:
        """Convert a single file or a directory (recursively or flat) mirroring structure."""
        start_total = time.perf_counter()
        input_path = input_path.resolve()

        if output_dir is None:
            output_dir = self.config.output_dir.resolve()
        else:
            output_dir = output_dir.resolve()

        output_dir.mkdir(parents=True, exist_ok=True)
        summary = PipelineSummary()

        if input_path.is_file():
            summary.total = 1
            out_file = output_dir / f"{input_path.stem}.md"
            item_res = self.convert_file(input_path, output_file=out_file)
            summary.results.append(item_res)
            if item_res.success:
                summary.succeeded += 1
            else:
                summary.failed += 1
            summary.duration_seconds = time.perf_counter() - start_total
            return summary

        if not input_path.is_dir():
            summary.failed += 1
            summary.results.append(
                PipelineItemResult(
                    source_path=input_path,
                    success=False,
                    error=f"Input path does not exist: {input_path}",
                )
            )
            summary.duration_seconds = time.perf_counter() - start_total
            return summary

        # Directory traversal
        supported_exts = set(list_supported_extensions())
        pattern = "**/*" if self.config.batch.recursive else "*"
        all_candidates = [p for p in input_path.glob(pattern) if p.is_file()]

        for p in all_candidates:
            if p.suffix.lower() not in supported_exts:
                continue

            summary.total += 1
            # Mirror directory structure relative to input_path
            rel = p.relative_to(input_path)
            target_file = (output_dir / rel).with_suffix(".md")
            target_assets = target_file.parent / self.config.images.folder

            try:
                item_res = self.convert_file(
                    source=p,
                    output_file=target_file,
                    assets_dir=target_assets,
                )
            except Exception as exc:
                if not self.config.batch.continue_on_error:
                    raise
                item_res = PipelineItemResult(
                    source_path=p,
                    success=False,
                    error=f"Unhandled pipeline error: {exc}",
                )

            summary.results.append(item_res)
            if item_res.success:
                summary.succeeded += 1
                logger.info("[OK] Converted: %s -> %s", p.name, target_file.name)
            else:
                summary.failed += 1
                logger.error("[FAIL] Failed %s: %s", p.name, item_res.error)

        summary.duration_seconds = time.perf_counter() - start_total
        return summary
