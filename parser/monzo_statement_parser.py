"""Parser for Monzo Business Account PDF statements."""

from __future__ import annotations

import logging
import re
from pathlib import Path
import pdfplumber

from parser.templates.base import RawRow

logger = logging.getLogger(__name__)

DATE_PREFIX = re.compile(r"^(\d{2}/\d{2}/\d{4})(?:\s+(.*))?$")
DATE_AMOUNT_BALANCE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
)
DATE_FULL = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
)
REFERENCE_ONLY = re.compile(r"^\d{3,8}$")
REFERENCE_LINE = re.compile(r"^reference:\s*.+", re.I)
CONTINUATION_LINE = re.compile(r"^[Pp]ayments\)\s*", re.I)
PAGE_MARKER = re.compile(r"^--\s*\d+\s+of\s+\d+\s+--", re.I)
SKIP_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"^date\s+description\s+amount\s+balance$",
        r"^monzo bank",
        r"^sort code:",
        r"^account number:",
        r"^iban:",
        r"^bic:",
        r"^https?://",
        r"^www\.",
        r"fscs",
        r"financial services compensation",
        r"registered office",
        r"important information",
        r"^business account statement",
        r"^total outgoings",
        r"^total deposits",
        r"balance in pots",
        r"excluding all pots",
        r"^\(gbp\)",
        r"prudential regulation",
        r"financial conduct authority",
        r"^great homes uk$",
        r"^parsons farm",
        r"^warren corner",
        r"^united kingdom",
        r"^petersfield",
        r"^business account balance",
    ]
]


def _normalize_line(line: str) -> str:
    line = line.replace("\ufffd", "").replace("£", "")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _row_quality(rows: list[RawRow]) -> float:
    from utils.amounts import parse_amount
    from utils.dates import parse_date

    if not rows:
        return 0.0
    good = 0
    for r in rows:
        if not parse_date(r.date, "uk") or parse_amount(r.amount) is None:
            continue
        d = r.description or ""
        if len(d) < 10:
            continue
        if re.search(r"fscs|730427|prudential|broadwalk", d, re.I):
            continue
        if re.match(r"^\(faster payments\)$", d, re.I):
            continue
        good += 1
    return good / len(rows)


def extract_monzo_statement(pdf_path: Path) -> list[RawRow]:
    """Extract Monzo transactions — picks best of layout vs text parsing."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error("Monzo parser: file not found %s", pdf_path)
        return []

    try:
        from parser.monzo_layout_parser import extract_monzo_layout

        layout_rows: list[RawRow] = []
        text_rows: list[RawRow] = []
        try:
            layout_rows = extract_monzo_layout(pdf_path)
        except Exception as e:
            logger.warning("Monzo layout failed: %s", e)
        try:
            text_rows = _extract_monzo_text(pdf_path)
        except Exception as e:
            logger.warning("Monzo text failed: %s", e)

        q_layout = _row_quality(layout_rows)
        q_text = _row_quality(text_rows)
        logger.info(
            "Monzo compare: layout=%d (q=%.2f) text=%d (q=%.2f)",
            len(layout_rows),
            q_layout,
            len(text_rows),
            q_text,
        )

        if q_text >= q_layout and text_rows:
            return text_rows
        if layout_rows:
            return layout_rows
        if text_rows:
            return text_rows

        from parser.emergency_extract import emergency_extract

        return emergency_extract(pdf_path)
    except Exception as e:
        logger.exception("Monzo extract failed: %s", e)
        return []


def _extract_monzo_text(pdf_path: Path) -> list[RawRow]:
    lines: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
    except Exception as e:
        logger.warning("Monzo text read failed: %s", e)
        return []
    return parse_monzo_lines(lines)


def _should_skip(line: str) -> bool:
    if not line:
        return True
    if PAGE_MARKER.search(line):
        return True
    if DATE_PREFIX.match(line) and " - " in line and line.count("/") >= 4:
        return True
    return any(p.search(line) for p in SKIP_PATTERNS)


def parse_monzo_lines(lines: list[str]) -> list[RawRow]:
    """Parse Monzo lines from pdfplumber extract_text order."""
    rows: list[RawRow] = []
    pending_desc: list[str] = []
    seen_table = False

    def flush(date: str, amount: str, balance: str, desc_parts: list[str]) -> None:
        desc = " ".join(p.strip() for p in desc_parts if p.strip())
        rows.append(
            RawRow(
                date=date,
                description=desc,
                amount=amount.replace(",", ""),
                balance=balance.replace(",", ""),
                source="monzo_text",
            )
        )

    for raw in lines:
        line = _normalize_line(raw)

        if re.search(r"date\s+description\s+amount", line, re.I):
            seen_table = True
            pending_desc = []
            continue

        if _should_skip(line):
            continue

        if DATE_AMOUNT_BALANCE.match(line) or DATE_FULL.match(line):
            seen_table = True

        if not seen_table:
            continue

        if PAGE_MARKER.search(line):
            pending_desc = []
            continue

        if rows and (
            REFERENCE_ONLY.match(line)
            or REFERENCE_LINE.match(line)
            or CONTINUATION_LINE.match(line)
        ):
            rows[-1].description = f"{rows[-1].description} {line}".strip()
            continue

        m_compact = DATE_AMOUNT_BALANCE.match(line)
        if m_compact:
            flush(m_compact.group(1), m_compact.group(2), m_compact.group(3), pending_desc)
            pending_desc = []
            continue

        m_full = DATE_FULL.match(line)
        if m_full:
            desc = m_full.group(2).strip()
            parts = pending_desc + ([desc] if desc else [])
            flush(m_full.group(1), m_full.group(3), m_full.group(4), parts)
            pending_desc = []
            continue

        date_m = DATE_PREFIX.match(line)
        if date_m and date_m.group(2):
            rest = date_m.group(2).strip()
            m_rest = re.match(r"^(.+?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$", rest)
            if m_rest:
                parts = pending_desc + [m_rest.group(1).strip()]
                flush(date_m.group(1), m_rest.group(2), m_rest.group(3), parts)
                pending_desc = []
                continue

        if not DATE_PREFIX.match(line):
            pending_desc.append(line)

    from parser.monzo_layout_parser import _sort_chronological

    return _sort_chronological(rows)
