"""Row-level validation and duplicate removal."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import config
from parser.templates.base import BankTemplate, RawRow
from utils.amounts import format_amount, parse_amount
from utils.dates import normalize_date_display, parse_date
from validators.continuity import check_balance_continuity

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    rows: list[RawRow]
    warnings: list[str] = field(default_factory=list)
    critical_errors: list[str] = field(default_factory=list)
    removed_duplicates: int = 0


class ValidationEngine:
    """Validate and clean extracted transaction rows."""

    def __init__(
        self,
        template: BankTemplate,
        validation_log_path: Optional[Path] = None,
    ) -> None:
        self.template = template
        self.validation_log_path = validation_log_path
        self.locale = template.locale

    def validate(self, rows: list[RawRow]) -> ValidationResult:
        result = ValidationResult(rows=[])
        seen_hashes: set[str] = set()

        for i, row in enumerate(rows):
            issues = self._validate_row(row, i)
            is_critical = any("critical" in w for w in issues)
            if is_critical:
                result.critical_errors.extend(issues)
                continue
            result.warnings.extend(issues)

            row_hash = self._row_hash(row)
            if row_hash in seen_hashes:
                result.removed_duplicates += 1
                result.warnings.append(f"Row {i}: duplicate removed")
                continue
            seen_hashes.add(row_hash)

            cleaned = self._normalize_row(row)
            result.rows.append(cleaned)

        continuity_warnings = check_balance_continuity(result.rows, self.locale)
        result.warnings.extend(continuity_warnings)

        result.warnings.append(f"Validated {len(result.rows)} transactions from {len(rows)} input rows")

        if self.validation_log_path:
            self._write_log(result)

        return result

    def _validate_row(self, row: RawRow, index: int) -> list[str]:
        issues: list[str] = []
        if not row.date or not parse_date(row.date, self.locale):
            issues.append(f"Row {index}: invalid date '{row.date}'")
        if parse_amount(row.amount) is None:
            issues.append(f"Row {index}: critical - invalid amount '{row.amount}'")
        if row.balance and parse_amount(row.balance) is None:
            issues.append(f"Row {index}: invalid balance '{row.balance}'")
        if not row.description.strip():
            issues.append(f"Row {index}: missing description")
        return issues

    def _normalize_row(self, row: RawRow) -> RawRow:
        amt = parse_amount(row.amount)
        bal = parse_amount(row.balance)
        return RawRow(
            date=normalize_date_display(row.date, self.locale),
            description=" ".join(row.description.split()),
            amount=format_amount(amt) if amt is not None else row.amount,
            balance=format_amount(bal) if bal is not None else (row.balance or ""),
            page=row.page,
            source=row.source,
            raw_cells=row.raw_cells,
        )

    def _row_hash(self, row: RawRow) -> str:
        key = f"{row.date}|{row.description}|{row.amount}"
        return hashlib.md5(key.encode()).hexdigest()

    def _write_log(self, result: ValidationResult) -> None:
        self.validation_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.validation_log_path, "w", encoding="utf-8") as f:
            for w in result.warnings:
                f.write(w + "\n")
            for e in result.critical_errors:
                f.write("ERROR: " + e + "\n")
