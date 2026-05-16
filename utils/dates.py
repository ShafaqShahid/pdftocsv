"""Locale-aware date parsing utilities."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import config

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_month_name(token: str) -> Optional[int]:
    key = token.lower()[:3]
    return _MONTH_MAP.get(key)


def parse_date(value: str | None, locale: str = "uk") -> Optional[datetime]:
    """Parse date string according to locale hints."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    # DD Mon YYYY
    m = re.match(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})",
        text,
        re.I,
    )
    if m:
        day, mon, year = int(m.group(1)), _parse_month_name(m.group(2)), int(m.group(3))
        if mon and 1 <= day <= 31:
            if year < 100:
                year += 2000
            try:
                return datetime(year, mon, day)
            except ValueError:
                pass

    # Mon DD, YYYY (US)
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{2,4})", text, re.I)
    if m and locale == "us":
        mon = _parse_month_name(m.group(1))
        day, year = int(m.group(2)), int(m.group(3))
        if mon:
            if year < 100:
                year += 2000
            try:
                return datetime(year, mon, day)
            except ValueError:
                pass

    separators = ["/", "-", ".", " "]
    for sep in separators:
        if sep in text:
            parts = [p for p in text.replace(",", "").split(sep) if p]
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
                if c < 100:
                    c += 2000
                try:
                    if locale == "us":
                        return datetime(c, a, b)
                    if locale == "eu" and sep == ".":
                        return datetime(c, b, a)
                    # UK default: DD/MM/YYYY
                    if a > 12:
                        return datetime(c, b, a)
                    if b > 12:
                        return datetime(c, a, b)
                    return datetime(c, b, a)
                except ValueError:
                    continue
    return None


def normalize_date_display(value: str | None, locale: str = "uk") -> str:
    """Normalize date to DD/MM/YYYY for CSV when parseable."""
    if not value:
        return ""
    parsed = parse_date(value, locale)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    return str(value).strip()


def line_starts_with_date(line: str, locale: str = "uk") -> bool:
    """Check if line begins with a date anchor."""
    anchor = config.DATE_ANCHORS.get(locale, config.DATE_ANCHORS["uk"])
    return bool(anchor.match(line.strip()))
