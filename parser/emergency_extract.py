"""Fast fallback: scan PDF text for date + amount + balance lines."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

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
    rows: list[RawRow] = []
    pending_desc: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                logger.error("PDF has zero pages: %s", pdf_path)
                return []

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    logger.warning("Page %d has no extractable text", page_num)
                    continue

                for raw in text.splitlines():
                    line = raw.replace("\ufffd", "").replace("£", "")
                    line = re.sub(r"\s+", " ", line).strip()
                    if not line:
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
                                page=page_num,
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
                                page=page_num,
                                source="emergency",
                            )
                        )
                        pending_desc = []
                        continue

                    if not TXN_COMPACT.match(line) and not re.match(
                        r"^\d{2}/\d{2}/\d{4}", line
                    ):
                        if len(line) > 3 and "monzo bank" not in line.lower():
                            pending_desc.append(line)

    except Exception as e:
        logger.exception("Emergency extract failed: %s", e)
        return []

    logger.info("Emergency extract: %d rows from %s", len(rows), pdf_path.name)
    return rows
