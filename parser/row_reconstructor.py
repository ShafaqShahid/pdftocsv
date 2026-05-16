"""Merge multi-line descriptions into single transaction rows."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from parser.templates.base import BankTemplate, RawRow
from utils.amounts import parse_amount
from utils.dates import line_starts_with_date

logger = logging.getLogger(__name__)


class RowReconstructor:
    """Merge wrapped description lines; split only on date anchors."""

    def __init__(
        self,
        template: BankTemplate,
        failed_rows_path: Optional[Path] = None,
    ) -> None:
        self.template = template
        self.failed_rows_path = failed_rows_path
        self._failed: list[dict] = []

    def reconstruct(self, rows: list[RawRow]) -> list[RawRow]:
        if not rows:
            return []

        # If rows already look complete, still run merge pass on descriptions
        merged: list[RawRow] = []
        current: RawRow | None = None
        locale = self.template.locale

        for row in rows:
            line_text = f"{row.date} {row.description}".strip()
            starts_with_date = line_starts_with_date(row.date, locale) or line_starts_with_date(
                line_text, locale
            )

            if starts_with_date and parse_amount(row.amount) is not None:
                if current:
                    merged.append(current)
                current = RawRow(
                    date=row.date,
                    description=row.description.strip(),
                    amount=row.amount,
                    balance=row.balance,
                    page=row.page,
                    source=row.source,
                    raw_cells=row.raw_cells,
                )
            elif current:
                if self._should_merge_into_previous(row, current):
                    current.description = (
                        f"{current.description} {row.description}".strip()
                    )
                    if row.amount and not current.amount:
                        current.amount = row.amount
                    if row.balance and not current.balance:
                        current.balance = row.balance
                else:
                    self._log_failed(row, "orphan_line")
                    if parse_amount(row.amount):
                        merged.append(row)
            else:
                if parse_amount(row.amount) and row.description:
                    merged.append(row)
                else:
                    self._log_failed(row, "no_anchor")

        if current:
            merged.append(current)

        self._flush_failed()
        logger.info("Reconstructed %d rows from %d input", len(merged), len(rows))
        return merged

    def _should_merge_into_previous(self, row: RawRow, current: RawRow) -> bool:
        """Merge if row has no date anchor and no standalone amount."""
        locale = self.template.locale
        if line_starts_with_date(row.date, locale):
            return False
        if line_starts_with_date(row.description, locale):
            return False
        if parse_amount(row.amount) and not row.description:
            return False
        return True

    def _log_failed(self, row: RawRow, reason: str) -> None:
        entry = {
            "reason": reason,
            "date": row.date,
            "description": row.description,
            "amount": row.amount,
            "balance": row.balance,
        }
        self._failed.append(entry)
        logger.debug("Failed row (%s): %s", reason, row.description[:50])

    def _flush_failed(self) -> None:
        if not self._failed or not self.failed_rows_path:
            return
        self.failed_rows_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.failed_rows_path, "a", encoding="utf-8") as f:
            for entry in self._failed:
                f.write(json.dumps(entry) + "\n")
        self._failed.clear()
