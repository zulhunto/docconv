"""Core data models for docconv."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from docconv.config import AppConfig


@dataclass
class Asset:
    """Represents an extracted asset (image, table image, etc.) from a document."""

    original_name: str
    saved_path: Path
    mime_type: str = "image/png"
    width: int = 0
    height: int = 0

    @property
    def markdown_ref(self) -> str:
        """Return a Markdown image reference."""
        return f"![{self.original_name}]({self.saved_path.as_posix()})"


@dataclass
class DocMetadata:
    """Metadata extracted from a source document."""

    title: str = ""
    author: str = ""
    created: str = ""
    modified: str = ""
    subject: str = ""
    keywords: list[str] = field(default_factory=list)
    page_count: int = 0
    source_format: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_frontmatter_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.title:
            d["title"] = self.title
        if self.author:
            d["author"] = self.author
        if self.created:
            d["date"] = self.created
        if self.subject:
            d["subject"] = self.subject
        if self.keywords:
            d["keywords"] = self.keywords
        if self.page_count:
            d["pages"] = self.page_count
        if self.source_format:
            d["source_format"] = self.source_format
        d.update(self.extra)
        return d


@dataclass
class ConvertContext:
    """Context passed to each converter during conversion."""

    output_dir: Path
    assets_dir: Path
    config: "AppConfig"
    ocr_enabled: bool = False
    ocr_lang: str = "ind+eng"
    extract_images: bool = True
    source_path: Path | None = None


@dataclass
class MarkdownResult:
    """Result of a single document conversion."""

    markdown: str
    metadata: DocMetadata = field(default_factory=DocMetadata)
    assets: list[Asset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    @classmethod
    def from_error(cls, message: str) -> "MarkdownResult":
        return cls(markdown="", error=message)
