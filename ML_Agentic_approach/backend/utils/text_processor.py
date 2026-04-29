"""
Text extraction utilities — handles txt, md, log, pdf, docx.
Mirrors the logic in evaluate_reports.py so both systems use the same text.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def read_file_text(file_path: str) -> str:
    """Read any supported file format and return plain text."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    # txt, md, log — plain text
    return _read_plaintext(path)


def read_bytes_text(data: bytes, filename: str) -> str:
    """Read from in-memory bytes (for uploaded files)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _read_pdf_bytes(data)
    if suffix == ".docx":
        return _read_docx_bytes(data)
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def normalize_text(text: str) -> str:
    """Collapse excess whitespace, unify line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Format-specific readers ───────────────────────────────────────────────────

def _read_plaintext(path: Path) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return path.read_text(errors="replace")


def _read_pdf(path: Path) -> str:
    return _read_pdf_bytes(path.read_bytes())


def _read_pdf_bytes(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except ImportError:
        logger.warning("pypdf not installed — returning empty string for PDF")
        return ""
    except Exception as e:
        logger.error(f"PDF read error: {e}")
        return ""


def _read_docx(path: Path) -> str:
    return _read_docx_bytes(path.read_bytes())


def _read_docx_bytes(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(para.text for para in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed — returning empty string for DOCX")
        return ""
    except Exception as e:
        logger.error(f"DOCX read error: {e}")
        return ""


def truncate_for_display(text: str, max_chars: int = 5000) -> str:
    """Return first max_chars characters with a truncation notice if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... {len(text) - max_chars} more characters truncated ...]"


def count_sentences(text: str) -> int:
    return len(re.findall(r"[.!?]+", text))


def count_paragraphs(text: str) -> int:
    return len([p for p in text.split("\n\n") if p.strip()])
