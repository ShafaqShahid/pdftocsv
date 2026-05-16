"""Running balance continuity checks."""

from __future__ import annotations

import config
from parser.templates.base import RawRow
from utils.amounts import parse_amount


def check_balance_continuity(rows: list[RawRow], locale: str) -> list[str]:
    """Warn if balances don't chain; skips reverse-order statements (e.g. Monzo)."""
    warnings: list[str] = []
    balances = [
        (i, parse_amount(r.balance))
        for i, r in enumerate(rows)
        if r.balance and parse_amount(r.balance) is not None
    ]
    if len(balances) < 3:
        return warnings

    forward_ok = 0
    reverse_ok = 0
    for n in range(1, len(balances)):
        _, prev_b = balances[n - 1]
        idx, cur_b = balances[n]
        amount = parse_amount(rows[idx].amount)
        if amount is None or prev_b is None or cur_b is None:
            continue
        if abs(float(prev_b + amount - cur_b)) <= config.BALANCE_TOLERANCE:
            forward_ok += 1
        if abs(float(cur_b + amount - prev_b)) <= config.BALANCE_TOLERANCE:
            reverse_ok += 1

    checks = max(len(balances) - 1, 1)
    if reverse_ok > forward_ok and reverse_ok >= checks * 0.6:
        return warnings
    if forward_ok < checks * 0.3 and checks >= 5:
        return warnings

    prev_balance = None
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
