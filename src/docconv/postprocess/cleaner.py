"""Postprocessing: header/footer removal, dehyphenation, and whitespace cleanup."""

from __future__ import annotations

import re


def _normalize_header_footer_text(text: str) -> str:
    """Normalize text by replacing digits/page counters to detect recurring patterns."""
    t = text.strip().lower()
    # Normalize numbers e.g. "Hal. 3", "Page 12 of 30", "3"
    t = re.sub(r"\b(page|hal|halaman)\.?\s*\d+(\s*(of|dari)\s*\d+)?\b", "<page>", t)
    t = re.sub(r"^\d+$", "<num>", t)
    t = re.sub(r"\d+", "<num>", t)
    return t


def strip_headers_and_footers(markdown: str) -> str:
    """Detect and remove recurring header/footer lines and standalone page numbers.

    Only operates outside fenced code blocks.
    """
    chunks = _split_code_blocks(markdown)
    processed_chunks: list[str] = []

    for is_code, text in chunks:
        if is_code:
            processed_chunks.append(text)
            continue

        # Split into pages if page breaks or form feeds exist
        # PyMuPDF often inserts \x0c or "-----\n" or page markers
        pages = re.split(r"(?:\n\s*---\s*\n|\x0c)", text)
        if len(pages) <= 1:
            # Just clean standalone page numbers
            cleaned_text = _remove_standalone_page_numbers(text)
            processed_chunks.append(cleaned_text)
            continue

        # Collect first and last lines across pages
        header_patterns: dict[str, int] = {}
        footer_patterns: dict[str, int] = {}
        page_lines_list: list[list[str]] = []

        for page in pages:
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            page_lines_list.append(lines)
            if lines:
                first_norm = _normalize_header_footer_text(lines[0])
                header_patterns[first_norm] = header_patterns.get(first_norm, 0) + 1
                if len(lines) > 1:
                    last_norm = _normalize_header_footer_text(lines[-1])
                    footer_patterns[last_norm] = footer_patterns.get(last_norm, 0) + 1

        num_pages = len(pages)
        threshold = max(2, num_pages // 2)

        recurring_headers = {
            pat for pat, count in header_patterns.items() if count >= threshold and pat
        }
        recurring_footers = {
            pat for pat, count in footer_patterns.items() if count >= threshold and pat
        }

        # Filter pages
        cleaned_pages = []
        for page in pages:
            lines = page.splitlines()
            if not lines:
                cleaned_pages.append(page)
                continue

            filtered_lines = []
            non_empty_indices = [i for i, l in enumerate(lines) if l.strip()]

            drop_indices = set()
            if non_empty_indices:
                first_idx = non_empty_indices[0]
                if _normalize_header_footer_text(lines[first_idx]) in recurring_headers:
                    drop_indices.add(first_idx)

            if len(non_empty_indices) > 1:
                last_idx = non_empty_indices[-1]
                if _normalize_header_footer_text(lines[last_idx]) in recurring_footers:
                    drop_indices.add(last_idx)

            for i, line in enumerate(lines):
                if i in drop_indices:
                    continue
                # Also strip standalone page numbers
                stripped = line.strip()
                if _is_standalone_page_number(stripped):
                    continue
                filtered_lines.append(line)

            cleaned_pages.append("\n".join(filtered_lines))

        processed_chunks.append("\n\n---\n\n".join(cleaned_pages))

    return "".join(processed_chunks)


def _is_standalone_page_number(line: str) -> bool:
    """Check if a line contains only a page number marker."""
    if not line:
        return False
    # Patterns: "1", "12", "- 12 -", "Page 1", "Hal. 4", "Halaman 5 of 10"
    if re.match(r"^[-–—\s]*\d+[-–—\s]*$", line):
        return True
    if re.match(r"^(page|hal|halaman)\.?\s*\d+(\s*(of|dari)\s*\d+)?$", line, re.IGNORECASE):
        return True
    return False


def _remove_standalone_page_numbers(text: str) -> str:
    lines = text.splitlines()
    res = [line for line in lines if not _is_standalone_page_number(line.strip())]
    return "\n".join(res)


def dehyphenate(markdown: str) -> str:
    """Connect words broken with a hyphen across lines when the next line begins with a lowercase letter.

    Preserves code blocks and markdown lists/indents.
    """
    chunks = _split_code_blocks(markdown)
    processed_chunks: list[str] = []

    # Match word ending with hyphen, newline, then word starting with lowercase
    # e.g. "penye- \nlesaian" -> "penyelesaian"
    # But exclude markdown list items, headers, table borders, etc.
    hyphen_pattern = re.compile(r"([A-Za-zÀ-ÿ]+)-\s*\n\s*([a-zà-ÿ]+)")

    for is_code, text in chunks:
        if is_code:
            processed_chunks.append(text)
        else:
            processed_chunks.append(hyphen_pattern.sub(r"\1\2", text))

    return "".join(processed_chunks)


def clean_whitespace(markdown: str, max_blank_lines: int = 1) -> str:
    """Collapse excess blank lines and strip trailing whitespace while preserving code blocks."""
    chunks = _split_code_blocks(markdown)
    processed_chunks: list[str] = []

    blank_limit = "\n" * (max_blank_lines + 1)
    blank_pattern = re.compile(r"\n{" + str(max_blank_lines + 2) + r",}")

    for is_code, text in chunks:
        if is_code:
            processed_chunks.append(text)
        else:
            # Strip trailing spaces on each line
            lines = [re.sub(r"[ \t]+$", "", line) for line in text.splitlines()]
            # Collapse multiple spaces within sentences (except leading markdown indents)
            cleaned_lines = []
            for line in lines:
                leading_spaces = len(line) - len(line.lstrip(" "))
                indent = line[:leading_spaces]
                rest = line[leading_spaces:]
                # Collapse double spaces in text
                rest = re.sub(r"[ \t]{2,}", " ", rest)
                cleaned_lines.append(indent + rest)
            joined = "\n".join(cleaned_lines)
            # Limit consecutive blank lines
            joined = blank_pattern.sub(blank_limit, joined)
            processed_chunks.append(joined)

    return "".join(processed_chunks).strip() + "\n"


def _split_code_blocks(text: str) -> list[tuple[bool, str]]:
    """Split text into (is_code_block, content) pairs."""
    pattern = re.compile(r"(```[\s\S]*?```|`[^`\n]+`)")
    chunks: list[tuple[bool, str]] = []
    last_end = 0

    for match in pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            chunks.append((False, text[last_end:start]))
        chunks.append((True, match.group(0)))
        last_end = end

    if last_end < len(text):
        chunks.append((False, text[last_end:]))

    return chunks


def clean_markdown(
    markdown: str,
    strip_headers_footers_flag: bool = True,
    dehyphenate_flag: bool = True,
    max_blank_lines: int = 1,
) -> str:
    """Run full cleaning pipeline on Markdown text."""
    res = markdown
    if strip_headers_footers_flag:
        res = strip_headers_and_footers(res)
    if dehyphenate_flag:
        res = dehyphenate(res)
    res = clean_whitespace(res, max_blank_lines=max_blank_lines)
    return res
