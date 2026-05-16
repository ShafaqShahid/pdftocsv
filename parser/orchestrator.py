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
from validators.row_validator import ValidationEngine

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single PDF."""

    success: bool
    template_name: str = ""
    locale: str = ""
    strategy: str = ""
    row_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    output_path: Path | None = None


class PipelineOrchestrator:
    """Detect template, extract, reconstruct, validate, write CSV."""

    def __init__(self, debug: bool = False, run_id: str = "") -> None:
        self.debug = debug
        self.run_id = run_id
        self.detector = BankTemplateDetector()
        self.extractor = TableExtractor(debug=debug)

    def run(self, pdf_path: Path, output_path: Path | None = None) -> ProcessingResult:
        """Process one PDF and return detailed result."""
        pdf_path = Path(pdf_path)
        out = ProcessingResult(success=False)

        logger.info("Processing: %s", pdf_path)
        template = self.detector.detect(pdf_path)
        out.template_name = template.name
        out.locale = template.locale
        logger.info("Template: %s, locale: %s", template.name, template.locale)

        rows, strategy = self.extractor.extract(pdf_path, template)
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
        out.warnings = validation.warnings

        for w in validation.warnings[:20]:
            logger.warning(w)

        if validation.critical_errors:
            out.errors.extend(validation.critical_errors)
            for e in validation.critical_errors:
                logger.error(e)
            return out

        if not validation.rows:
            out.errors.append("No valid rows after validation.")
            return out

        out.row_count = len(validation.rows)
        if output_path:
            output_path = Path(output_path)
            generate_csv(validation.rows, output_path)
            out.output_path = output_path

        out.success = True
        return out

    def process(self, pdf_path: Path, output_path: Path) -> bool:
        """Process one PDF. Returns True on success."""
        return self.run(pdf_path, output_path).success
