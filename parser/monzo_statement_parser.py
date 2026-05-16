"""Parser for Monzo Business Account PDF statements."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from parser.templates.base import RawRow

logger = logging.getLogger(__name__)

DATE_PREFIX = re.compile(r"^(\d{2}/\d{2}/\d{4})(?:\s+(.*))?$")
# Date then amount then balance (description in prior lines)
DATE_AMOUNT_BALANCE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
)
# Date, description..., amount, balance on one line
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
    line = line.replace("\ufffd", "").replace("£", "").replace("", "")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def extract_monzo_statement(pdf_path: Path) -> list[RawRow]:
    """Extract transactions from Monzo Business statement PDF."""
    lines: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
    except Exception as e:
        logger.warning("Monzo text read failed: %s", e)
        return []

    rows = parse_monzo_lines(lines)
    logger.info("Monzo parser extracted %d rows from %s", len(rows), pdf_path.name)
    return rows


def _should_skip(line: str) -> bool:
    if not line:
        return True
    if PAGE_MARKER.search(line):
        return True
    if DATE_PREFIX.match(line) and " - " in line and line.count("/") >= 4:
        # Statement period: 01/04/2026 - 01/05/2026
        return True
    return any(p.search(line) for p in SKIP_PATTERNS)


def parse_monzo_lines(lines: list[str]) -> list[RawRow]:
    """
    Parse Monzo lines from pdfplumber text order.

    pdfplumber often outputs description lines *before* the date+amount+balance line.
    """
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

        if not seen_table:
            continue

        if PAGE_MARKER.search(line):
            pending_desc = []
            continue

        # Reference / continuation attached to previous transaction
        if rows and (
            REFERENCE_ONLY.match(line)
            or REFERENCE_LINE.match(line)
            or CONTINUATION_LINE.match(line)
        ):
            rows[-1].description = f"{rows[-1].description} {line}".strip()
            continue

        m_compact = DATE_AMOUNT_BALANCE.match(line)
        if m_compact:
            flush(
                m_compact.group(1),
                m_compact.group(2),
                m_compact.group(3),
                pending_desc,
            )
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
            m_rest = re.match(
                r"^(.+?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$",
                rest,
            )
            if m_rest:
                parts = pending_desc + [m_rest.group(1).strip()]
                flush(date_m.group(1), m_rest.group(2), m_rest.group(3), parts)
                pending_desc = []
                continue

        # Description fragment (appears before date line in pdfplumber output)
        if not DATE_PREFIX.match(line):
            pending_desc.append(line)

    return rows
