"""Barclays bank statement template."""

from __future__ import annotations

from parser.templates.base import BankTemplate


class BarclaysTemplate(BankTemplate):
    name = "barclays"
    locale = "uk"
    keywords = ["barclays", "barclays bank", "sortcode", "sort code"]

    def detect_score(self, pdf_text: str, first_page_tables: list[list[list[str]]]) -> float:
        text = pdf_text.lower()
        score = 0.0
        if "barclays" in text:
            score += 0.55
        for kw in self.keywords:
            if kw in text:
                score += 0.1
        return min(score, 1.0)
