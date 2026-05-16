"""Monzo bank statement template."""

from __future__ import annotations

from typing import Optional

from parser.templates.base import BankTemplate, NormalizedRow
from utils.amounts import parse_amount


class MonzoTemplate(BankTemplate):
    name = "monzo"
    locale = "uk"
    keywords = [
        "monzo",
        "faster payment",
        "monzo bank",
        "business account statement",
        "monzo.com",
    ]

    def detect_score(self, pdf_text: str, first_page_tables: list[list[list[str]]]) -> float:
        text = pdf_text.lower()
        score = 0.0
        if "monzo" in text:
            score += 0.4
        if "business account statement" in text:
            score += 0.35
        for kw in self.keywords:
            if kw in text:
                score += 0.15
        return min(score, 1.0)

    def normalize_row(self, cells: list[str]) -> Optional[NormalizedRow]:
        cells = [str(c).strip() if c else "" for c in cells]
        lower_headers = {"money out", "money in", "amount", "balance"}
        if cells and cells[0].lower() in lower_headers:
            return None

        # Monzo often: Date | Description | (Money out) | (Money in) | Balance
        if len(cells) >= 4:
            date = cells[0]
            if not self.is_transaction_row([date]):
                base = super().normalize_row(cells)
                return base

            description_parts = []
            money_out = ""
            money_in = ""
            balance = ""

            for i, c in enumerate(cells[1:], start=1):
                cl = c.lower()
                if cl in ("money out", "money in"):
                    continue
                if parse_amount(c) is not None:
                    if i == len(cells) - 1:
                        balance = c
                    elif not money_out and not money_in:
                        money_out = c
                    elif money_out and not money_in:
                        money_in = c
                    else:
                        balance = c
                else:
                    description_parts.append(c)

            amount = self.merge_money_in_out(money_out, money_in)
            if not amount:
                result = super().normalize_row(cells)
                return result

            return NormalizedRow(
                date=date,
                description=" ".join(description_parts).strip(),
                amount=amount,
                balance=balance,
            )

        return super().normalize_row(cells)
