"""Logging setup: rich console handler + rotating file handler."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from rich.logging import RichHandler

_configured = False


def setup_logging(
    log_file: Path | None = None,
    level: int = logging.INFO,
    verbose: bool = False,
) -> logging.Logger:
    """Configure root logger with console (rich) + optional file handler.

    Safe to call multiple times; only configures once.
    """
    global _configured
    if _configured:
        return logging.getLogger("docconv")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else level)

    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    # --- Console handler (rich) ---
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        level=logging.DEBUG if verbose else level,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    root.addHandler(console_handler)

    # --- File handler ---
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(file_handler)

    _configured = True
    return logging.getLogger("docconv")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
