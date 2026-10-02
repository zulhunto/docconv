"""YAML Front Matter handling for generated Markdown."""

from __future__ import annotations

import yaml
from docconv.models import DocMetadata


def format_frontmatter(metadata: DocMetadata, content: str) -> str:
    """Prepend YAML front matter to markdown content if metadata is present."""
    data = metadata.to_frontmatter_dict()
    if not data:
        return content

    yaml_str = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()

    return f"---\n{yaml_str}\n---\n\n{content}"
