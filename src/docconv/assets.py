"""Asset manager: saves extracted images/media with unique names."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PIL import Image

from docconv.models import Asset

logger = logging.getLogger(__name__)


class AssetManager:
    """Handles saving of extracted assets (images, etc.) to a directory."""

    def __init__(self, assets_dir: Path, min_size_px: int = 64) -> None:
        self.assets_dir = assets_dir
        self.min_size_px = min_size_px
        self._seen: dict[str, int] = {}  # stem → counter for deduplication
        assets_dir.mkdir(parents=True, exist_ok=True)

    def save_image_bytes(
        self,
        data: bytes,
        hint_name: str = "image",
        suffix: str = ".png",
    ) -> Asset | None:
        """Save raw image bytes to the assets directory.

        Returns None if image is too small or data is empty.
        """
        if not data:
            return None

        try:
            from io import BytesIO

            img = Image.open(BytesIO(data))
            w, h = img.size
            if w < self.min_size_px or h < self.min_size_px:
                logger.debug(
                    "Skipping small image %s (%dx%d < %dpx)",
                    hint_name, w, h, self.min_size_px,
                )
                return None
            mime = Image.MIME.get(img.format or "PNG", "image/png")
            # Normalize suffix from format
            fmt = (img.format or "PNG").lower()
            suffix = f".{fmt}" if fmt else suffix
        except Exception as exc:
            logger.warning("Cannot open image %s: %s", hint_name, exc)
            return None

        # Build unique filename
        stem = Path(hint_name).stem or "image"
        content_hash = hashlib.md5(data).hexdigest()[:8]
        count = self._seen.get(stem, 0)
        self._seen[stem] = count + 1
        filename = f"{stem}_{content_hash}{suffix}" if count == 0 else f"{stem}_{content_hash}_{count}{suffix}"

        dest = self.assets_dir / filename
        dest.write_bytes(data)
        logger.debug("Saved asset: %s", dest)

        return Asset(
            original_name=hint_name,
            saved_path=dest,
            mime_type=mime,
            width=w,
            height=h,
        )

    def save_pil_image(
        self,
        img: Image.Image,
        hint_name: str = "image",
        fmt: str = "PNG",
    ) -> Asset | None:
        """Save a PIL Image object to the assets directory."""
        from io import BytesIO

        buf = BytesIO()
        img.save(buf, format=fmt)
        return self.save_image_bytes(buf.getvalue(), hint_name=hint_name, suffix=f".{fmt.lower()}")

    def save_file(self, src: Path, hint_name: str | None = None) -> Asset | None:
        """Copy an existing image file into the assets directory."""
        if not src.exists():
            return None
        data = src.read_bytes()
        return self.save_image_bytes(data, hint_name=hint_name or src.name, suffix=src.suffix)
