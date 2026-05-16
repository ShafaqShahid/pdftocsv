"""End-to-end pipeline orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from csv_generator import generate_csv
from parser.bank_detector import BankTemplateDetector
from parser.extractor import TableExtractor
from parser.header_footer import HeaderFooterCleaner
from parser.row_reconstructor import RowReconstructor
from parser.templates.base import RawRow
from utils.logging_setup import get_failed_rows_path, get_validation_log_path
from utils.amounts import parse_amount
from validators.row_validator import ValidationEngine

logger = logging.getLogger(__name__)


def _best_effort_rows(rows: list[RawRow]) -> list[RawRow]:
    """Include rows that have enough data to be useful in a partial CSV."""
    kept: list[RawRow] = []
    for row in rows:
        has_amount = parse_amount(row.amount) is not None
        has_text = bool(row.description.strip()) or bool(row.date.strip())
        if has_amount or (has_text and row.date):
            kept.append(row)
    return kept


@dataclass
class ProcessingResult:
    """Result of processing a single PDF."""

    success: bool
    partial: bool = False
    template_name: str = ""
    locale: str = ""
    strategy: str = ""
    row_count: int = 0
    rows_extracted: int = 0
    rows_rejected: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    output_path: Path | None = None


class PipelineOrchestrator:
    """Detect template, extract, reconstruct, validate, write CSV."""

    def __init__(
        self,
        debug: bool = False,
        run_id: str = "",
        fast_mode: bool | None = None,
    ) -> None:
        self.debug = debug
        self.run_id = run_id
        self.detector = BankTemplateDetector()
        self.extractor = TableExtractor(debug=debug, fast_mode=fast_mode)
        self._on_progress = None

    def set_progress_callback(self, callback) -> None:
        self._on_progress = callback

    def _progress(self, msg: str) -> None:
        if self._on_progress:
            self._on_progress(msg)

    def run(self, pdf_path: Path, output_path: Path | None = None) -> ProcessingResult:
        """Process one PDF and return detailed result."""
        pdf_path = Path(pdf_path)
        out = ProcessingResult(success=False)

        logger.info("Processing: %s", pdf_path)
        self._progress("Detecting bank template…")
        template = self.detector.detect(pdf_path)
        out.template_name = template.name
        out.locale = template.locale
        logger.info("Template: %s, locale: %s", template.name, template.locale)

        rows, strategy = self.extractor.extract(
            pdf_path, template, on_progress=self._on_progress
        )
        out.strategy = strategy
        if not rows:
            out.errors.append("No transactions could be extracted from this PDF.")
            logger.error("No transactions extracted from %s", pdf_path)
            return out

        logger.info("Extraction strategy: %s (%d raw rows)", strategy, len(rows))

        cleaner = HeaderFooterCleaner()
        rows = cleaner.clean(rows)

        failed_path = get_failed_rows_path(self.run_id) if self.run_id else None
        reconstructor = RowReconstructor(template, failed_path)
        rows = reconstructor.reconstruct(rows)

        validation_path = get_validation_log_path(self.run_id) if self.run_id else None
        validator = ValidationEngine(template, validation_path)
        validation = validator.validate(rows)
        out.warnings = list(validation.warnings)
        out.rows_extracted = len(rows)
        out.rows_rejected = len(validation.critical_errors)

        for w in validation.warnings[:20]:
            logger.warning(w)

        if validation.critical_errors:
            out.errors.extend(validation.critical_errors[:50])
            if len(validation.critical_errors) > 50:
                out.errors.append(
                    f"... and {len(validation.critical_errors) - 50} more row errors"
                )
            for e in validation.critical_errors[:10]:
                logger.error(e)

        export_rows = validation.rows
        if not export_rows:
            export_rows = _best_effort_rows(rows)
            if export_rows:
                out.warnings.append(
                    f"Best-effort export: {len(export_rows)} rows "
                    f"(validation failed for {len(rows)} extracted rows)."
                )

        if not export_rows:
            out.errors.append("No valid rows after validation.")
            return out

        out.row_count = len(export_rows)
        has_validation_issues = bool(validation.critical_errors) or len(export_rows) < len(rows)

        if output_path:
            output_path = Path(output_path)
            generate_csv(export_rows, output_path)
            out.output_path = output_path

        if has_validation_issues:
            out.partial = True
            out.warnings.insert(
                0,
                f"Partial export: {out.row_count} of {len(rows)} extracted rows included in CSV.",
            )
            logger.warning("Partial CSV written: %d rows", out.row_count)
        else:
            out.success = True

        return out

    def process(self, pdf_path: Path, output_path: Path) -> bool:
        """Process one PDF. Returns True if full success or partial CSV written."""
        result = self.run(pdf_path, output_path)
        return result.success or result.partial
