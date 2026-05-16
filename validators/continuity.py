"""Running balance continuity checks."""

from __future__ import annotations

import config
from parser.templates.base import RawRow
from utils.amounts import parse_amount


def check_balance_continuity(rows: list[RawRow], locale: str) -> list[str]:
    """Warn if prev_balance + amount != balance when balances are present."""
    warnings: list[str] = []
    prev_balance = None

    balances_present = sum(1 for r in rows if r.balance and parse_amount(r.balance))
    if balances_present < 2:
        return warnings

    for i, row in enumerate(rows):
        amount = parse_amount(row.amount)
        balance = parse_amount(row.balance)
        if balance is None:
            continue
        if prev_balance is not None and amount is not None:
            expected = prev_balance + amount
            diff = abs(float(expected - balance))
            if diff > config.BALANCE_TOLERANCE:
                warnings.append(
                    f"Row {i}: balance continuity mismatch "
                    f"(expected {expected:.2f}, got {balance:.2f})"
                )
        prev_balance = balance

    return warnings
