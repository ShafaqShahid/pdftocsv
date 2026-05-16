"""Extraction orchestrator with fallback chain and quality scoring."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Callable, Optional

import config
from parser.camelot_extractor import extract_with_camelot
from parser.monzo_statement_parser import extract_monzo_statement
from parser.pdfplumber_extractor import extract_with_pdfplumber
from parser.regex_extractor import extract_with_regex
from parser.templates.base import BankTemplate, RawRow
from utils.amounts import parse_amount
from utils.dates import parse_date

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


class TableExtractor:
    """Try extraction strategies in order until quality threshold is met."""

    def __init__(self, debug: bool = False, fast_mode: bool | None = None) -> None:
        self.debug = debug
        self.fast_mode = config.FAST_MODE if fast_mode is None else fast_mode

    def extract(
        self,
        pdf_path: Path,
        template: BankTemplate,
        on_progress: Optional[ProgressCallback] = None,
    ) -> tuple[list[RawRow], str]:
        """Return (rows, strategy_name) using best successful extractor."""
        if self.fast_mode:
            strategy_names = list(config.FAST_EXTRACTION_STRATEGIES)
            if template.name == "monzo" and "monzo_text" not in strategy_names:
                strategy_names.insert(0, "monzo_text")
        else:
            strategy_names = list(config.EXTRACTION_STRATEGIES)
            if template.name == "monzo":
                strategy_names = ["monzo_text"] + [
                    s for s in strategy_names if s != "monzo_text"
                ]

        strategies = [
            (name, self._strategy_fn(name, pdf_path, template))
            for name in strategy_names
        ]

        best_rows: list[RawRow] = []
        best_strategy = ""
        best_score = 0.0

        for name, fn in strategies:
            if on_progress:
                on_progress(f"Trying {name}…")
            timeout = config.STRATEGY_TIMEOUT_SECONDS.get(name, 60)
            try:
                rows = _run_with_timeout(fn, timeout)
            except Exception as e:
                logger.warning("Strategy %s error: %s", name, e)
                if on_progress:
                    on_progress(f"{name} failed: {e}")
                continue

            if not rows:
                logger.debug("Strategy %s returned no rows", name)
                if on_progress:
                    on_progress(f"{name}: no rows")
                continue

            score = quality_score(rows, template)
            logger.info("Strategy %s: %d rows, quality=%.2f", name, len(rows), score)
            if on_progress:
                on_progress(f"{name}: {len(rows)} rows (quality {score:.0%})")

            if score >= config.QUALITY_SCORE_THRESHOLD:
                return rows, name

            if score > best_score:
                best_score = score
                best_rows = rows
                best_strategy = name

        if best_rows:
            logger.info("Using best fallback %s (quality=%.2f)", best_strategy, best_score)
            return best_rows, best_strategy

        return [], ""

    def _strategy_fn(self, name: str, pdf_path: Path, template: BankTemplate):
        if name == "monzo_text":
            return lambda: extract_monzo_statement(pdf_path)
        if name == "camelot_lattice":
            return lambda: extract_with_camelot(pdf_path, template, "lattice", self.debug)
        if name == "camelot_stream":
            return lambda: extract_with_camelot(pdf_path, template, "stream", self.debug)
        if name == "pdfplumber":
            return lambda: extract_with_pdfplumber(pdf_path, template, self.debug)
        if name == "regex":
            return lambda: extract_with_regex(pdf_path, template, self.debug)
        raise ValueError(f"Unknown strategy: {name}")


def _run_with_timeout(fn, timeout: int):
    """Run extractor in a thread; return [] on timeout."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            logger.warning("Strategy timed out after %ds", timeout)
            return []


def quality_score(rows: list[RawRow], template: BankTemplate) -> float:
    """Fraction of rows with valid date and amount."""
    if not rows:
        return 0.0
    valid = 0
    for row in rows:
        has_date = bool(row.date and parse_date(row.date, template.locale))
        has_amount = parse_amount(row.amount) is not None
        if has_date and has_amount:
            valid += 1
    return valid / len(rows)
