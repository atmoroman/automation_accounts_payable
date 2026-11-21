"""PDF -> plain text."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def pdf_to_text(path: str | Path) -> str:
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if not text:
        # Scanned PDFs are images with no text layer -> would need OCR (e.g. Tesseract).
        raise ValueError(
            f"No text layer found in {path}. This looks like a scanned PDF; OCR is not supported yet."
        )
    return text
