"""Generic UK-style bank statement template."""

from __future__ import annotations

from parser.templates.base import BankTemplate


class GenericTemplate(BankTemplate):
    name = "generic"
    locale = "uk"
    keywords = ["statement", "account", "transaction", "balance"]

    def detect_score(self, pdf_text: str, first_page_tables: list[list[list[str]]]) -> float:
        text = pdf_text.lower()
        score = 0.1
        for kw in self.keywords:
            if kw in text:
                score += 0.05
        if "date" in text and ("description" in text or "details" in text):
            score += 0.15
        return min(score, 0.35)
