"""Remove headers, footers, and repeated page titles from row lists."""

from __future__ import annotations

import logging

import config
from parser.templates.base import RawRow

logger = logging.getLogger(__name__)


class HeaderFooterCleaner:
    """Filter non-transaction rows and repeated headers."""

    def __init__(self) -> None:
        self._seen_header_signature: str | None = None

    def clean(self, rows: list[RawRow]) -> list[RawRow]:
        cleaned: list[RawRow] = []
        for row in rows:
            if self._is_header_row(row):
                sig = self._header_signature(row)
                if self._seen_header_signature is None:
                    self._seen_header_signature = sig
                continue
            if self._is_footer_row(row):
                logger.debug("Dropped footer row: %s", row.description[:40])
                continue
            if self._is_page_number(row):
                continue
            cleaned.append(row)
        return cleaned

    def _header_signature(self, row: RawRow) -> str:
        parts = [row.date, row.description, row.amount, row.balance]
        return "|".join(p.lower().strip() for p in parts)

    def _is_header_row(self, row: RawRow) -> bool:
        text = " ".join(
            filter(None, [row.date, row.description, row.amount, row.balance])
        ).lower()
        if not text:
            return True
        for pattern in config.HEADER_PATTERNS:
            if pattern.search(row.date or "") or pattern.search(row.description or ""):
                if not row.amount and not parse_amount_safe(row.balance):
                    return True
        # Repeated column header line
        header_words = {"date", "description", "details", "amount", "balance", "paid out", "paid in"}
        tokens = set(text.split())
        if tokens and tokens <= header_words:
            return True
        return False

    def _is_footer_row(self, row: RawRow) -> bool:
        combined = f"{row.description} {row.date} {row.balance}".lower()
        for kw in config.FOOTER_KEYWORDS:
            if kw in combined:
                if not parse_amount_safe(row.amount):
                    return True
        if "total" in combined and "payment" in combined:
            return True
        return False

    def _is_page_number(self, row: RawRow) -> bool:
        for field in (row.description, row.date, row.balance):
            if field and config.PAGE_NUMBER_PATTERN.match(field.strip()):
                return True
        return False


def parse_amount_safe(value: str) -> bool:
    from utils.amounts import parse_amount

    return parse_amount(value) is not None
