"""Extraction orchestrator with fallback chain and quality scoring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import config
from parser.camelot_extractor import extract_with_camelot
from parser.pdfplumber_extractor import extract_with_pdfplumber
from parser.regex_extractor import extract_with_regex
from parser.templates.base import BankTemplate, RawRow
from utils.amounts import parse_amount
from utils.dates import parse_date

logger = logging.getLogger(__name__)


class TableExtractor:
    """Try extraction strategies in order until quality threshold is met."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    def extract(self, pdf_path: Path, template: BankTemplate) -> tuple[list[RawRow], str]:
        """Return (rows, strategy_name) using best successful extractor."""
        strategies = [
            ("camelot_lattice", lambda: extract_with_camelot(pdf_path, template, "lattice", self.debug)),
            ("camelot_stream", lambda: extract_with_camelot(pdf_path, template, "stream", self.debug)),
            ("pdfplumber", lambda: extract_with_pdfplumber(pdf_path, template, self.debug)),
            ("regex", lambda: extract_with_regex(pdf_path, template, self.debug)),
        ]

        best_rows: list[RawRow] = []
        best_strategy = ""
        best_score = 0.0

        for name, fn in strategies:
            try:
                rows = fn()
            except Exception as e:
                logger.warning("Strategy %s error: %s", name, e)
                continue

            if not rows:
                logger.debug("Strategy %s returned no rows", name)
                continue

            score = quality_score(rows, template)
            logger.info("Strategy %s: %d rows, quality=%.2f", name, len(rows), score)

            if score >= config.QUALITY_SCORE_THRESHOLD:
                return rows, name

            if score > best_score:
                best_score = score
                best_rows = rows
                best_strategy = name

        if best_rows:
            logger.info("Using best fallback %s (quality=%.2f)", best_strategy, best_score)
            return best_rows, best_strategy

        return [], ""


def quality_score(rows: list[RawRow], template: BankTemplate) -> float:
    """Fraction of rows with valid date and amount."""
    if not rows:
        return 0.0
    valid = 0
    for row in rows:
        has_date = bool(row.date and parse_date(row.date, template.locale))
        has_amount = parse_amount(row.amount) is not None
        if has_date and has_amount:
            valid += 1
    return valid / len(rows)
