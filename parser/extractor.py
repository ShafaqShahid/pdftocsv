"""Extraction orchestrator with fallback chain and quality scoring."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Callable, Optional

import config
from parser.camelot_extractor import extract_with_camelot
from parser.emergency_extract import emergency_extract
from parser.monzo_statement_parser import extract_monzo_statement
from parser.pdfplumber_extractor import extract_with_pdfplumber
from parser.regex_extractor import extract_with_regex
from parser.templates.base import BankTemplate, RawRow
from utils.amounts import parse_amount
from utils.dates import parse_date

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]

# Strategies that must run on main thread (pdfplumber + threads = issues on Streamlit Cloud)
INLINE_STRATEGIES = frozenset({"monzo", "monzo_text", "monzo_layout"})


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
        pdf_path = Path(pdf_path)
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            logger.error("PDF missing or empty: %s", pdf_path)
            return [], ""

        strategy_names = self._strategy_list(template)

        best_rows: list[RawRow] = []
        best_strategy = ""
        best_score = 0.0
        last_error = ""

        for name in strategy_names:
            if on_progress:
                on_progress(f"Trying {name}…")

            try:
                fn = self._strategy_fn(name, pdf_path, template)
                timeout = config.STRATEGY_TIMEOUT_SECONDS.get(name, 60)
                if name in INLINE_STRATEGIES or self.fast_mode:
                    rows = fn()
                else:
                    rows = _run_with_timeout(fn, timeout)
            except Exception as e:
                last_error = str(e)
                logger.exception("Strategy %s error", name)
                if on_progress:
                    on_progress(f"{name} failed: {e}")
                continue

            if not rows:
                if on_progress:
                    on_progress(f"{name}: no rows")
                continue

            score = quality_score(rows, template)
            logger.info("Strategy %s: %d rows, quality=%.2f", name, len(rows), score)
            if on_progress:
                on_progress(f"{name}: {len(rows)} rows (quality {score:.0%})")

            if score >= config.QUALITY_SCORE_THRESHOLD and score >= best_score:
                return rows, name

            if score > best_score or (rows and not best_rows):
                best_score = score
                best_rows = rows
                best_strategy = name

        if best_rows:
            return best_rows, best_strategy

        if on_progress:
            on_progress("Trying emergency scan…")
        try:
            rows = emergency_extract(pdf_path)
            if rows:
                if on_progress:
                    on_progress(f"emergency: {len(rows)} rows")
                return rows, "emergency"
        except Exception as e:
            last_error = str(e)
            logger.exception("Emergency extract failed")

        if on_progress and last_error:
            on_progress(f"All strategies failed. Last error: {last_error}")

        return [], ""

    def _strategy_list(self, template: BankTemplate) -> list[str]:
        if self.fast_mode:
            names = list(config.FAST_EXTRACTION_STRATEGIES)
        else:
            names = list(config.EXTRACTION_STRATEGIES)

        if template.name == "monzo":
            for s in ("monzo", "monzo_text"):
                if s not in names:
                    names.insert(0, s)

        if self.fast_mode and config.SKIP_REGEX_IN_FAST_MODE:
            names = [n for n in names if n != "regex"]

        return names

    def _strategy_fn(self, name: str, pdf_path: Path, template: BankTemplate):
        if name in ("monzo", "monzo_text", "monzo_layout"):
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
    """Score rows: date, amount, description length, no junk."""
    if not rows:
        return 0.0
    valid = 0
    for row in rows:
        has_date = bool(row.date and parse_date(row.date, template.locale))
        has_amount = parse_amount(row.amount) is not None
        desc = (row.description or "").strip()
        desc_ok = len(desc) >= 3
        if has_date and has_amount and desc_ok:
            valid += 1
    return valid / len(rows)
