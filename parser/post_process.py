"""Post-processing: dedupe, clean, filter junk rows."""

from __future__ import annotations

import re

from parser.templates.base import RawRow
from utils.amounts import parse_amount
from utils.dates import parse_date

JUNK_DESC = re.compile(
    r"monzo bank|broadwalk house|prudential regulation|sort code|"
    r"financial services compensation|financial services register|"
    r"730427|fscs|authorised by the|regulated by the|"
    r"^reference:\s*$|for protection under",
    re.I,
)

WEAK_DESC = re.compile(
    r"^\(faster payments\)$|^\(faster payments\)\s*$",
    re.I,
)


def post_process_rows(rows: list[RawRow], locale: str = "uk") -> list[RawRow]:
    """Clean and filter extracted rows."""
    cleaned: list[RawRow] = []
    seen: set[str] = set()

    for row in rows:
        if not row.date or not parse_date(row.date, locale):
            continue
        if parse_amount(row.amount) is None:
            continue
        desc = re.sub(r"\s+", " ", row.description or "").strip()
        if len(desc) < 2 or JUNK_DESC.search(desc):
            continue
        if WEAK_DESC.match(desc):
            continue
        if len(desc) < 12 and not re.search(
            r"reference:|direct debit|faster payment|transfer|expenses", desc, re.I
        ):
            continue

        key = f"{row.date}|{desc}|{row.amount}|{row.balance}"
        if key in seen:
            continue
        seen.add(key)

        row.description = desc
        cleaned.append(row)

    return cleaned
