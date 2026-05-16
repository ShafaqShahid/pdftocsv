"""Monzo statement parser using word positions (x/y) for accurate columns."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from parser.templates.base import RawRow
from utils.amounts import parse_amount
from utils.dates import parse_date

logger = logging.getLogger(__name__)

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
AMOUNT_RE = re.compile(r"^-?[\d,]+\.\d{2}$")
SKIP_Y_TEXT = re.compile(
    r"monzo bank|sort code|account number|iban|bic|fscs|prudential|"
    r"financial conduct|registered office|total outgoings|total deposits|"
    r"business account statement|important information|\(gbp\)",
    re.I,
)


@dataclass
class ColumnBounds:
    date_max: float = 120.0
    desc_max: float = 385.0
    amount_max: float = 465.0


def extract_monzo_layout(pdf_path: Path) -> list[RawRow]:
    """Extract Monzo transactions using pdfplumber word coordinates."""
    all_rows: list[RawRow] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            bounds = _detect_column_bounds(pdf)
            for page_num, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(use_text_flow=True) or []
                if not words:
                    words = page.extract_words() or []
                page_rows = _parse_page_words(
                    words, page_num, bounds, page.height or 800.0
                )
                all_rows.extend(page_rows)
    except Exception as e:
        logger.warning("Monzo layout extraction failed: %s", e)
        return []

    all_rows = _merge_continuations(all_rows)
    all_rows = _sort_chronological(all_rows)
    logger.info("Monzo layout extracted %d rows from %s", len(all_rows), pdf_path.name)
    return all_rows


def _detect_column_bounds(pdf) -> ColumnBounds:
    """Infer column x boundaries from header row 'Date Description Amount Balance'."""
    bounds = ColumnBounds()
    for page in pdf.pages[:2]:
        words = page.extract_words() or []
        headers = [w for w in words if w["text"].lower() in ("date", "amount", "balance")]
        desc_h = [w for w in words if w["text"].lower() == "description"]
        if headers:
            date_h = next((w for w in headers if w["text"].lower() == "date"), None)
            amt_h = next((w for w in headers if w["text"].lower() == "amount"), None)
            bal_h = next((w for w in headers if w["text"].lower() == "balance"), None)
            if date_h and amt_h:
                bounds.date_max = (date_h["x0"] + amt_h["x0"]) / 2
                bounds.desc_max = amt_h["x0"] - 5
            if amt_h and bal_h:
                bounds.amount_max = (amt_h["x0"] + bal_h["x0"]) / 2
    return bounds


def _column_for_word(word: dict, bounds: ColumnBounds) -> str:
    x = word["x0"]
    if x < bounds.date_max:
        return "date"
    if x < bounds.desc_max:
        return "desc"
    if x < bounds.amount_max:
        return "amount"
    return "balance"


def _group_lines(words: list[dict], y_tol: float = 4.0) -> list[list[dict]]:
    if not words:
        return []
    sorted_w = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines: list[list[dict]] = []
    cur: list[dict] = []
    cur_y: float | None = None
    for w in sorted_w:
        y = w["top"]
        if cur_y is None or abs(y - cur_y) <= y_tol:
            cur.append(w)
            cur_y = y if cur_y is None else (cur_y + y) / 2
        else:
            if cur:
                lines.append(sorted(cur, key=lambda x: x["x0"]))
            cur = [w]
            cur_y = y
    if cur:
        lines.append(sorted(cur, key=lambda x: x["x0"]))
    return lines


def _line_to_fields(line_words: list[dict], bounds: ColumnBounds) -> dict[str, str]:
    cols: dict[str, list[str]] = defaultdict(list)
    for w in line_words:
        cols[_column_for_word(w, bounds)].append(w["text"])
    return {k: " ".join(v).strip() for k, v in cols.items()}


def _parse_page_words(
    words: list[dict], page_num: int, bounds: ColumnBounds, page_height: float = 800.0
) -> list[RawRow]:
    rows: list[RawRow] = []
    pending_desc: list[str] = []
    accept_tail = False

    for line_words in _group_lines(words):
        if line_words and line_words[0].get("top", 0) > page_height * 0.82:
            avg_x = sum(w["x0"] for w in line_words) / len(line_words)
            if avg_x < bounds.date_max + 50:
                continue
        if not line_words:
            continue
        line_text = " ".join(w["text"] for w in line_words)
        if SKIP_Y_TEXT.search(line_text):
            continue
        if "date description amount balance" in line_text.lower():
            pending_desc = []
            accept_tail = False
            continue

        fields = _line_to_fields(line_words, bounds)
        date = fields.get("date", "").strip()
        desc = fields.get("desc", "").strip()
        amount = fields.get("amount", "").replace("£", "").strip()
        balance = fields.get("balance", "").replace("£", "").strip()

        # Date may be glued in desc column on some lines
        if not DATE_RE.match(date) and desc:
            dm = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.*)$", desc)
            if dm:
                date = dm.group(1)
                desc = dm.group(2).strip()

        has_date = DATE_RE.match(date)
        has_amounts = AMOUNT_RE.match(amount) and AMOUNT_RE.match(balance)

        if has_date and has_amounts:
            full_desc = " ".join(pending_desc + ([desc] if desc else [])).strip()
            rows.append(
                RawRow(
                    date=date,
                    description=_clean_description(full_desc),
                    amount=amount.replace(",", ""),
                    balance=balance.replace(",", ""),
                    page=page_num,
                    source="monzo_layout",
                )
            )
            pending_desc = []
            accept_tail = True
            continue

        if has_date and amount and not balance:
            # amount only in amount col
            if AMOUNT_RE.match(amount):
                full_desc = " ".join(pending_desc + ([desc] if desc else [])).strip()
                rows.append(
                    RawRow(
                        date=date,
                        description=_clean_description(full_desc),
                        amount=amount.replace(",", ""),
                        balance="",
                        page=page_num,
                        source="monzo_layout",
                    )
                )
                pending_desc = []
                accept_tail = True
                continue

        if accept_tail and rows and not has_date:
            tail = " ".join(filter(None, [desc, amount, balance])).strip()
            if tail and not SKIP_Y_TEXT.search(tail) and not _is_junk_tail(tail):
                rows[-1].description = _clean_description(
                    f"{rows[-1].description} {tail}".strip()
                )
            continue

        if not has_date and (desc or amount):
            if desc and not AMOUNT_RE.match(desc):
                pending_desc.append(desc)
            elif desc:
                pending_desc.append(desc)

    return rows


def _merge_continuations(rows: list[RawRow]) -> list[RawRow]:
    """Merge rows that were split (orphan description-only rows)."""
    if not rows:
        return []
    merged: list[RawRow] = []
    for row in rows:
        if (
            merged
            and not parse_amount(row.amount)
            and row.description
            and parse_date(merged[-1].date)
        ):
            merged[-1].description = _clean_description(
                f"{merged[-1].description} {row.description}".strip()
            )
        else:
            merged.append(row)
    return merged


def _is_junk_tail(text: str) -> bool:
    return bool(
        re.search(
            r"730427|financial services|compensation scheme|prudential|"
            r"registered in england",
            text,
            re.I,
        )
    )


def _clean_description(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("(Faster Payments )", "(Faster Payments)")
    return text


def _sort_chronological(rows: list[RawRow]) -> list[RawRow]:
    """Monzo PDFs list newest-first; sort oldest-first for CSV usability."""

    def sort_key(r: RawRow):
        d = parse_date(r.date, "uk")
        return d or __import__("datetime").datetime.min

    return sorted(rows, key=sort_key)
