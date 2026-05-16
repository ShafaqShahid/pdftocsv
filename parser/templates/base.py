"""Abstract bank template for statement parsing."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import config
from utils.amounts import parse_amount
from utils.dates import line_starts_with_date, parse_date


@dataclass
class RawRow:
    """A single extracted transaction row before validation."""

    date: str = ""
    description: str = ""
    amount: str = ""
    balance: str = ""
    page: int = 0
    source: str = ""
    raw_cells: list[str] = field(default_factory=list)


@dataclass
class NormalizedRow:
    """Standard four-column row."""

    date: str
    description: str
    amount: str
    balance: str


class BankTemplate(ABC):
    """Base class for bank-specific parsing rules."""

    name: str = "generic"
    locale: str = "uk"
    keywords: list[str] = []

    @abstractmethod
    def detect_score(self, pdf_text: str, first_page_tables: list[list[list[str]]]) -> float:
        """Return confidence 0-1 that this template matches the PDF."""

    def date_pattern(self) -> re.Pattern[str]:
        return config.DATE_ANCHORS.get(self.locale, config.DATE_ANCHORS["uk"])

    def amount_pattern(self) -> re.Pattern[str]:
        return config.AMOUNT_PATTERN

    def balance_pattern(self) -> re.Pattern[str]:
        return config.AMOUNT_AT_END

    def column_x_ranges(self, page: Any) -> Optional[list[tuple[float, float]]]:
        """Optional x-bound hints for positional column splitting."""
        return None

    def is_transaction_row(self, cells: list[str]) -> bool:
        """True if row looks like a transaction (not header/footer)."""
        if not cells:
            return False
        joined = " ".join(str(c) for c in cells if c).strip()
        if not joined:
            return False
        lower = joined.lower()
        for kw in config.FOOTER_KEYWORDS:
            if kw in lower and len(joined) < 80:
                return False
        first = str(cells[0]).strip() if cells[0] else ""
        if line_starts_with_date(first, self.locale) or line_starts_with_date(joined, self.locale):
            return True
        if self._has_amount(cells):
            return bool(first) and len(joined) > 5
        return False

    def _has_amount(self, cells: list[str]) -> bool:
        for c in cells:
            if c and parse_amount(str(c)) is not None:
                return True
        return False

    def normalize_row(self, cells: list[str]) -> Optional[NormalizedRow]:
        """Map raw table cells to standard four columns."""
        if not cells:
            return None
        cells = [str(c).strip() if c else "" for c in cells]
        joined = " ".join(c for c in cells if c)

        if not self.is_transaction_row(cells):
            return None

        date = self._extract_date(cells, joined)
        if not date:
            return None

        amount, balance = self._extract_amount_balance(cells, joined)
        if amount is None:
            return None

        description = self._extract_description(cells, date, amount, balance)
        return NormalizedRow(
            date=date,
            description=description,
            amount=amount or "",
            balance=balance or "",
        )

    def _extract_date(self, cells: list[str], joined: str) -> str:
        for c in cells:
            if c and (line_starts_with_date(c, self.locale) or parse_date(c, self.locale)):
                m = self.date_pattern().search(c)
                if m:
                    return m.group(1).strip() if m.lastindex else c.strip()
                return c.strip()
        m = self.date_pattern().search(joined)
        return m.group(1).strip() if m else ""

    def _extract_amount_balance(
        self, cells: list[str], joined: str
    ) -> tuple[Optional[str], str]:
        amounts: list[tuple[int, str]] = []
        for i, c in enumerate(cells):
            if c and parse_amount(c) is not None:
                amounts.append((i, c))
        if not amounts:
            matches = list(config.AMOUNT_PATTERN.finditer(joined))
            if matches:
                if len(matches) >= 2:
                    return matches[-2].group(0).strip(), matches[-1].group(0).strip()
                return matches[-1].group(0).strip(), ""
            return None, ""
        if len(amounts) >= 2:
            return amounts[-2][1], amounts[-1][1]
        return amounts[-1][1], ""

    def _extract_description(
        self,
        cells: list[str],
        date: str,
        amount: Optional[str],
        balance: str,
    ) -> str:
        skip = {date, amount or "", balance}
        parts = []
        for c in cells:
            c = c.strip()
            if c and c not in skip and not parse_amount(c):
                if not line_starts_with_date(c, self.locale):
                    parts.append(c)
        return " ".join(parts).strip()

    def merge_money_in_out(self, money_out: str, money_in: str) -> str:
        """Combine separate debit/credit columns into signed amount."""
        out_val = parse_amount(money_out)
        in_val = parse_amount(money_in)
        if in_val and in_val > 0:
            return str(in_val)
        if out_val:
            return str(-abs(out_val))
        return money_out or money_in or ""
