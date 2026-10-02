"""Converter registry: maps file extensions to converter classes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docconv.converters.base import BaseConverter

logger = logging.getLogger(__name__)

# extension (lowercase, with dot) → converter class
_ext_registry: dict[str, type["BaseConverter"]] = {}
# ordered list for sniff-based fallback
_all_converters: list[type["BaseConverter"]] = []


def register(cls: type["BaseConverter"]) -> type["BaseConverter"]:
    """Class decorator to register a converter.

    Usage::

        @register
        class MyConverter(BaseConverter):
            extensions = (".xyz",)
            ...
    """
    for ext in cls.extensions:
        key = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        if key in _ext_registry:
            logger.debug(
                "Overriding converter for %s: %s → %s",
                key, _ext_registry[key].__name__, cls.__name__,
            )
        _ext_registry[key] = cls
    if cls not in _all_converters:
        _all_converters.append(cls)
    logger.debug("Registered %s for %s", cls.__name__, cls.extensions)
    return cls


def get_converter(path: Path) -> "BaseConverter | None":
    """Return an instantiated converter that can handle *path*, or None."""
    ext = path.suffix.lower()

    # 1. Fast path: extension lookup
    if ext in _ext_registry:
        instance = _ext_registry[ext]()
        if instance.can_handle(path):
            return instance

    # 2. Slow path: try all converters (content sniffing via can_handle)
    for cls in _all_converters:
        instance = cls()
        try:
            if instance.can_handle(path):
                return instance
        except Exception:
            continue

    return None


def list_supported_extensions() -> list[str]:
    """Return sorted list of all registered extensions."""
    return sorted(_ext_registry.keys())
