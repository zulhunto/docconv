"""Configuration loading and validation using Pydantic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class OcrConfig(BaseModel):
    enabled: bool = True
    lang: str = "ind+eng"
    auto_detect: bool = True
    min_chars_per_page: int = 25


class ImagesConfig(BaseModel):
    extract: bool = True
    folder: str = "assets"
    min_size_px: int = 64


class PdfConfig(BaseModel):
    engine: str = "pymupdf4llm"  # or "docling"

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        allowed = {"pymupdf4llm", "docling"}
        if v not in allowed:
            raise ValueError(f"pdf.engine must be one of {allowed}")
        return v


class CleaningConfig(BaseModel):
    strip_headers_footers: bool = True
    dehyphenate: bool = True
    max_blank_lines: int = 1


class TablesConfig(BaseModel):
    fallback_html_on_merged_cells: bool = True


class BatchConfig(BaseModel):
    recursive: bool = True
    continue_on_error: bool = True


class AppConfig(BaseModel):
    output_dir: Path = Path("./out")
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    pdf: PdfConfig = Field(default_factory=PdfConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    tables: TablesConfig = Field(default_factory=TablesConfig)
    batch: BatchConfig = Field(default_factory=BatchConfig)


_SEARCH_NAMES = ("config.yaml", "docconv.yaml", "docconv.yml")


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate configuration from a YAML file.

    Search order:
    1. Explicit *path* argument
    2. config.yaml / docconv.yaml in the current directory
    3. Built-in defaults (no file found)
    """
    if path is None:
        for name in _SEARCH_NAMES:
            candidate = Path(name)
            if candidate.exists():
                path = candidate
                break

    if path and path.exists():
        with open(path, "r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        return AppConfig.model_validate(raw)

    return AppConfig()
