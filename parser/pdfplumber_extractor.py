"""pdfplumber-based table and positional extraction."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pdfplumber

import config
from parser.templates.base import BankTemplate, NormalizedRow, RawRow
from utils.amounts import parse_amount
from utils.dates import line_starts_with_date

logger = logging.getLogger(__name__)


def extract_with_pdfplumber(
    pdf_path: Path,
    template: BankTemplate,
    debug: bool = False,
) -> list[RawRow]:
    """Extract transaction rows page-by-page via tables and word clustering."""
    rows: list[RawRow] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_rows = _extract_page_tables(page, page_num, template)
                if not page_rows:
                    page_rows = _extract_page_words(page, page_num, template)
                rows.extend(page_rows)
    except Exception as e:
        logger.warning("pdfplumber extraction failed: %s", e)
        return []

    if debug and config.DEBUG_SAVE_INTERMEDIATE:
        config.DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = config.DEBUG_DIR / f"{pdf_path.stem}_pdfplumber.json"
        path.write_text(
            json.dumps([{"date": r.date, "desc": r.description[:50]} for r in rows[:20]]),
            encoding="utf-8",
        )

    logger.info("pdfplumber extracted %d rows from %s", len(rows), pdf_path.name)
    return rows


def _extract_page_tables(page: Any, page_num: int, template: BankTemplate) -> list[RawRow]:
    rows: list[RawRow] = []
    tables = page.extract_tables() or []
    for table in tables:
        if not table:
            continue
        for raw_row in table:
            cells = [str(c).strip() if c else "" for c in raw_row]
            norm = template.normalize_row(cells)
            if norm:
                rows.append(
                    RawRow(
                        date=norm.date,
                        description=norm.description,
                        amount=norm.amount,
                        balance=norm.balance,
                        page=page_num,
                        source="pdfplumber_table",
                        raw_cells=cells,
                    )
                )
    return rows


def _extract_page_words(page: Any, page_num: int, template: BankTemplate) -> list[RawRow]:
    """Positional fallback: cluster words by x0 into columns, group by y."""
    words = page.extract_words(keep_blank_chars=False) or []
    if not words:
        return []

    lines = _group_words_into_lines(words)
    rows: list[RawRow] = []
    for line_words in lines:
        cells = _line_to_cells(line_words, template)
        if not cells:
            continue
        norm = template.normalize_row(cells)
        if norm:
            rows.append(
                RawRow(
                    date=norm.date,
                    description=norm.description,
                    amount=norm.amount,
                    balance=norm.balance,
                    page=page_num,
                    source="pdfplumber_words",
                    raw_cells=cells,
                )
            )
    return rows


def _group_words_into_lines(words: list[dict], y_tolerance: float = 3.0) -> list[list[dict]]:
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines: list[list[dict]] = []
    current: list[dict] = []
    current_y: float | None = None

    for w in sorted_words:
        y = w["top"]
        if current_y is None or abs(y - current_y) <= y_tolerance:
            current.append(w)
            current_y = y if current_y is None else (current_y + y) / 2
        else:
            if current:
                lines.append(sorted(current, key=lambda x: x["x0"]))
            current = [w]
            current_y = y
    if current:
        lines.append(sorted(current, key=lambda x: x["x0"]))
    return lines


def _line_to_cells(line_words: list[dict], template: BankTemplate) -> list[str]:
    """Split a line of words into cells using x-clustering."""
    if not line_words:
        return []
    text = " ".join(w["text"] for w in line_words)
    if not text.strip():
        return []

    # Simple column split: date | middle | amounts at end
    locale = template.locale
    if line_starts_with_date(text, locale):
        date_match = template.date_pattern().search(text)
        date = date_match.group(1).strip() if date_match else ""
        remainder = text[date_match.end() :].strip() if date_match else text

        amounts = []
        desc = remainder
        import re

        amount_matches = list(config.AMOUNT_PATTERN.finditer(remainder))
        if amount_matches:
            last = amount_matches[-1]
            balance = last.group(0).strip()
            if len(amount_matches) >= 2:
                amount = amount_matches[-2].group(0).strip()
                desc = remainder[: amount_matches[-2].start()].strip()
            else:
                amount = balance
                balance = ""
                desc = remainder[: last.start()].strip()
            return [date, desc, amount, balance]
        return [date, remainder]
    return [text]


def rows_from_normalized(
    normalized: list[NormalizedRow],
    page: int,
    source: str,
) -> list[RawRow]:
    return [
        RawRow(
            date=n.date,
            description=n.description,
            amount=n.amount,
            balance=n.balance,
            page=page,
            source=source,
        )
        for n in normalized
    ]
