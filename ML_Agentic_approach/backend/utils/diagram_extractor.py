"""
Best-effort extraction of embedded diagram/figure images for VLM review.
"""
from __future__ import annotations

import base64
import io
import logging
import zipfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def extract_diagram_images(data: bytes, filename: str, limit: int = 4) -> List[str]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_images(data, limit)
    if suffix == ".docx":
        return _extract_docx_images(data, limit)
    return []


def _to_data_url(image_data: bytes, mime: str) -> str:
    encoded = base64.b64encode(image_data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _extract_pdf_images(data: bytes, limit: int) -> List[str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        images: List[str] = []
        for page in reader.pages:
            for image in getattr(page, "images", []):
                raw = image.data
                ext = Path(getattr(image, "name", "")).suffix.lower()
                mime = _MIME_BY_EXT.get(ext, "image/png")
                images.append(_to_data_url(raw, mime))
                if len(images) >= limit:
                    return images
        return images
    except Exception as exc:
        logger.info("PDF diagram extraction skipped: %s", exc)
        return []


def _extract_docx_images(data: bytes, limit: int) -> List[str]:
    try:
        images: List[str] = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                if not name.startswith("word/media/"):
                    continue
                ext = Path(name).suffix.lower()
                mime = _MIME_BY_EXT.get(ext)
                if not mime:
                    continue
                images.append(_to_data_url(archive.read(name), mime))
                if len(images) >= limit:
                    return images
        return images
    except Exception as exc:
        logger.info("DOCX diagram extraction skipped: %s", exc)
        return []
