"""Regex and line-anchor based text extraction fallback."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

import config
from parser.templates.base import BankTemplate, RawRow
from utils.amounts import parse_amount
from utils.dates import line_starts_with_date

logger = logging.getLogger(__name__)


def extract_with_regex(
    pdf_path: Path,
    template: BankTemplate,
    debug: bool = False,
) -> list[RawRow]:
    """Parse PDF text line-by-line using date anchors and trailing amounts."""
    rows: list[RawRow] = []
    locale = template.locale

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                page_rows = _parse_text_lines(text, page_num, template, locale)
                rows.extend(page_rows)
    except Exception as e:
        logger.warning("Regex extraction failed: %s", e)
        return []

    logger.info("Regex extracted %d rows from %s", len(rows), pdf_path.name)
    return rows


def _parse_text_lines(
    text: str,
    page_num: int,
    template: BankTemplate,
    locale: str,
) -> list[RawRow]:
    rows: list[RawRow] = []
    pending: RawRow | None = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line_starts_with_date(line, locale):
            if pending:
                rows.append(pending)
            parsed = _parse_transaction_line(line, template, locale)
            if parsed:
                parsed.page = page_num
                parsed.source = "regex"
                pending = parsed
        elif pending:
            # Continuation of description (no date at start, no sole amount line)
            if not _is_footer_line(line) and not line_starts_with_date(line, locale):
                trailing_amount = config.AMOUNT_AT_END.search(line)
                if trailing_amount and parse_amount(trailing_amount.group(0)):
                    pending.amount = trailing_amount.group(0).strip()
                    pending.description = (
                        pending.description + " " + line[: trailing_amount.start()]
                    ).strip()
                else:
                    pending.description = (pending.description + " " + line).strip()
        else:
            parsed = _parse_transaction_line(line, template, locale)
            if parsed:
                parsed.page = page_num
                parsed.source = "regex"
                rows.append(parsed)

    if pending:
        rows.append(pending)
    return rows


def _parse_transaction_line(
    line: str,
    template: BankTemplate,
    locale: str,
) -> RawRow | None:
    date_match = template.date_pattern().search(line)
    if not date_match:
        return None

    date = date_match.group(1).strip() if date_match.lastindex else date_match.group(0).strip()
    remainder = line[date_match.end() :].strip()

    amount_matches = list(config.AMOUNT_PATTERN.finditer(remainder))
    if not amount_matches:
        return None

    balance = ""
    amount = ""
    if len(amount_matches) >= 2:
        amount = amount_matches[-2].group(0).strip()
        balance = amount_matches[-1].group(0).strip()
        desc_end = amount_matches[-2].start()
    else:
        amount = amount_matches[-1].group(0).strip()
        desc_end = amount_matches[-1].start()

    description = remainder[:desc_end].strip()
    cells = [date, description, amount, balance]
    norm = template.normalize_row(cells)
    if norm:
        return RawRow(
            date=norm.date,
            description=norm.description,
            amount=norm.amount,
            balance=norm.balance,
            raw_cells=cells,
        )
    return RawRow(
        date=date,
        description=description,
        amount=amount,
        balance=balance,
        raw_cells=cells,
    )


def _is_footer_line(line: str) -> bool:
    lower = line.lower()
    if config.PAGE_NUMBER_PATTERN.match(line):
        return True
    for kw in config.FOOTER_KEYWORDS:
        if kw in lower and len(line) < 100:
            return True
    return False
