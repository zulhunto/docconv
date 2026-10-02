"""Plain text and JSON document converter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from docconv.converters.base import BaseConverter
from docconv.models import ConvertContext, DocMetadata, MarkdownResult
from docconv.registry import register


@register
class TextConverter(BaseConverter):
    """Converts plain text (.txt, .log) and JSON (.json) files to Markdown."""

    extensions: ClassVar[tuple[str, ...]] = (".txt", ".text", ".log", ".json")

    def convert(self, path: Path, ctx: ConvertContext) -> MarkdownResult:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return MarkdownResult.from_error(f"Failed to read text file: {exc}")

        ext = path.suffix.lower()
        title = path.stem.replace("_", " ").title()

        if ext == ".json":
            try:
                parsed = json.loads(content)
                pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                md = f"# {title}\n\n```json\n{pretty_json}\n```\n"
            except Exception:
                md = f"# {title}\n\n```json\n{content}\n```\n"
            meta = DocMetadata(title=title, source_format="JSON")
        else:
            md = f"# {title}\n\n{content}\n"
            meta = DocMetadata(title=title, source_format="Text")

        return MarkdownResult(markdown=md, metadata=meta)
