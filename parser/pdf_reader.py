"""Read PDF text — pdfplumber first, pypdf fallback (works better on Streamlit Cloud)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_pdf_lines(pdf_path: Path) -> list[str]:
    """Return all lines of text from PDF using best available backend."""
    pdf_path = Path(pdf_path)
    lines = _read_pdfplumber(pdf_path)
    if _has_content(lines):
        logger.info("PDF text via pdfplumber: %d lines", len(lines))
        return lines

    lines = _read_pypdf(pdf_path)
    if _has_content(lines):
        logger.info("PDF text via pypdf fallback: %d lines", len(lines))
        return lines

    logger.error("No text extracted from PDF: %s", pdf_path)
    return []


def read_pdf_page_text(pdf_path: Path, page_index: int = 0) -> str:
    """Text from a single page (for diagnostics)."""
    pdf_path = Path(pdf_path)
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            if page_index < len(pdf.pages):
                return pdf.pages[page_index].extract_text() or ""
    except Exception as e:
        logger.warning("pdfplumber page read: %s", e)

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        if page_index < len(reader.pages):
            return reader.pages[page_index].extract_text() or ""
    except Exception as e:
        logger.warning("pypdf page read: %s", e)
    return ""


def pdf_page_count(pdf_path: Path) -> int:
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        pass
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 0


def _read_pdfplumber(pdf_path: Path) -> list[str]:
    lines: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
    except Exception as e:
        logger.warning("pdfplumber failed: %s", e)
    return lines


def _read_pypdf(pdf_path: Path) -> list[str]:
    lines: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            text = page.extract_text() or ""
            lines.extend(text.splitlines())
    except Exception as e:
        logger.warning("pypdf failed: %s", e)
    return lines


def _has_content(lines: list[str]) -> bool:
    return sum(1 for ln in lines if ln.strip()) > 5
