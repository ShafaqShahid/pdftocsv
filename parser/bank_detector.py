"""Detect bank template from PDF content."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pdfplumber

import config
from parser.pdf_reader import read_pdf_lines, read_pdf_page_text
from parser.templates.base import BankTemplate
from parser.templates.barclays import BarclaysTemplate
from parser.templates.generic import GenericTemplate
from parser.templates.hsbc import HsbcTemplate
from parser.templates.monzo import MonzoTemplate

logger = logging.getLogger(__name__)

ALL_TEMPLATES: list[BankTemplate] = [
    MonzoTemplate(),
    HsbcTemplate(),
    BarclaysTemplate(),
    GenericTemplate(),
]


class BankTemplateDetector:
    """Select best-matching bank template for a PDF."""

    def __init__(self, templates: Optional[list[BankTemplate]] = None) -> None:
        self.templates = templates or ALL_TEMPLATES

    def detect(self, pdf_path: Path) -> BankTemplate:
        text, first_tables = self._read_pdf_preview(pdf_path)
        best: BankTemplate = GenericTemplate()
        best_score = 0.0

        for template in self.templates:
            if isinstance(template, GenericTemplate):
                continue
            score = template.detect_score(text, first_tables)
            logger.debug("Template %s score=%.2f", template.name, score)
            if score > best_score:
                best_score = score
                best = template

        if best_score < config.TEMPLATE_DETECT_THRESHOLD:
            generic = GenericTemplate()
            logger.info(
                "No strong template match (best=%.2f). Using generic.",
                best_score,
            )
            return generic

        logger.info("Detected bank template: %s (score=%.2f)", best.name, best_score)
        return best

    def _read_pdf_preview(
        self, pdf_path: Path
    ) -> tuple[str, list[list[list[str]]]]:
        lines = read_pdf_lines(pdf_path)
        text = "\n".join(lines)
        if not text.strip():
            text = read_pdf_page_text(pdf_path, 0)

        first_tables: list[list[list[str]]] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    tables = pdf.pages[0].extract_tables() or []
                    first_tables = [
                        [[str(c) if c else "" for c in row] for row in tbl]
                        for tbl in tables
                        if tbl
                    ]
        except Exception as e:
            logger.warning("Table preview failed: %s", e)

        return text, first_tables
