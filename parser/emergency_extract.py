"""Fast fallback: scan PDF text for date + amount + balance lines."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from parser.pdf_reader import read_pdf_lines
from parser.templates.base import RawRow

logger = logging.getLogger(__name__)

TXN_LINE = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
)
TXN_COMPACT = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
)


def emergency_extract(pdf_path: Path) -> list[RawRow]:
    """Last-resort extraction when other strategies return nothing."""
    lines = read_pdf_lines(pdf_path)
    if not lines:
        return []

    rows: list[RawRow] = []
    pending_desc: list[str] = []

    for raw in lines:
        line = raw.replace("\ufffd", "").replace("£", "")
        line = re.sub(r"\s+", " ", line).strip()
        if not line or "monzo bank limited" in line.lower():
            continue

        compact = TXN_COMPACT.match(line)
        if compact:
            desc = " ".join(pending_desc).strip()
            rows.append(
                RawRow(
                    date=compact.group(1),
                    description=desc,
                    amount=compact.group(2).replace(",", ""),
                    balance=compact.group(3).replace(",", ""),
                    source="emergency",
                )
            )
            pending_desc = []
            continue

        full = TXN_LINE.match(line)
        if full:
            rows.append(
                RawRow(
                    date=full.group(1),
                    description=full.group(2).strip(),
                    amount=full.group(3).replace(",", ""),
                    balance=full.group(4).replace(",", ""),
                    source="emergency",
                )
            )
            pending_desc = []
            continue

        if not re.match(r"^\d{2}/\d{2}/\d{4}", line):
            if len(line) > 2:
                pending_desc.append(line)

    logger.info("Emergency extract: %d rows from %s", len(rows), pdf_path.name)
    return rows
