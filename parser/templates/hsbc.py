"""HSBC bank statement template."""

from __future__ import annotations

from parser.templates.base import BankTemplate


class HsbcTemplate(BankTemplate):
    name = "hsbc"
    locale = "uk"
    keywords = ["hsbc", "hsbc uk", "sort code", "hsbc bank"]

    def detect_score(self, pdf_text: str, first_page_tables: list[list[list[str]]]) -> float:
        text = pdf_text.lower()
        score = 0.0
        if "hsbc" in text:
            score += 0.5
        for kw in self.keywords:
            if kw in text:
                score += 0.15
        if "paid out" in text or "paid in" in text:
            score += 0.1
        return min(score, 1.0)

    def normalize_row(self, cells: list[str]):
        cells = [str(c).strip() if c else "" for c in cells]
        # HSBC: Date | Description | Paid out | Paid in | Balance
        if len(cells) >= 5:
            date = cells[0]
            if self.is_transaction_row([date]):
                paid_out = cells[2] if len(cells) > 2 else ""
                paid_in = cells[3] if len(cells) > 3 else ""
                balance = cells[4] if len(cells) > 4 else ""
                desc = cells[1]
                amount = self.merge_money_in_out(paid_out, paid_in)
                if amount:
                    from parser.templates.base import NormalizedRow

                    return NormalizedRow(
                        date=date,
                        description=desc,
                        amount=amount,
                        balance=balance,
                    )
        return super().normalize_row(cells)
