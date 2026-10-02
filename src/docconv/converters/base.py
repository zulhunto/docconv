"""Abstract base class for all document converters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from docconv.models import ConvertContext, MarkdownResult


class BaseConverter(ABC):
    """Abstract base converter interface."""

    extensions: ClassVar[tuple[str, ...]] = ()

    def can_handle(self, path: Path) -> bool:
        """Check whether this converter can handle the given path.

        Default implementation checks the file extension.
        Subclasses may override to inspect magic bytes / file contents.
        """
        if not path.is_file():
            return False
        ext = path.suffix.lower()
        normalized_exts = tuple(
            e.lower() if e.startswith(".") else f".{e.lower()}"
            for e in self.extensions
        )
        return ext in normalized_exts

    @abstractmethod
    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        """Convert document at *path* to a MarkdownResult."""
        raise NotImplementedError
