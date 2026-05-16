"""Amount parsing and formatting utilities."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

import config


def parse_amount(value: str | None) -> Optional[Decimal]:
    """Parse monetary string to Decimal. Returns None if unparseable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in ("-", "—", "–"):
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    elif text.startswith("-"):
        negative = True
        text = text[1:].strip()

    # Remove currency symbols and spaces
    text = re.sub(r"[£$€\s]", "", text)
    # UK/US: comma thousands
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text and "." not in text:
        # Could be EU decimal comma
        parts = text.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            text = parts[0].replace(".", "") + "." + parts[1]
        else:
            text = text.replace(",", "")

    try:
        amount = Decimal(text)
        return -amount if negative else amount
    except (InvalidOperation, ValueError):
        return None


def format_amount(value: Decimal | float | str | None) -> str:
    """Format amount for CSV output."""
    if value is None or value == "":
        return ""
    parsed = value if isinstance(value, Decimal) else parse_amount(str(value))
    if parsed is None:
        return str(value)
    return f"{parsed:.2f}"


def extract_amounts_from_line(line: str) -> list[str]:
    """Find all amount-like tokens in a line."""
    return [m.group(0).strip() for m in config.AMOUNT_PATTERN.finditer(line)]
