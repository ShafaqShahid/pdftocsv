#!/usr/bin/env python3
"""CLI for PDF bank statement to CSV extraction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from parser.orchestrator import PipelineOrchestrator
from utils.logging_setup import setup_logging
from utils.paths import is_pdf, list_pdfs, output_csv_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract bank statement transactions from PDF to CSV.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input PDF file or directory of PDFs",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Output CSV file or directory for batch mode",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and save intermediate extraction artifacts",
    )
    return parser.parse_args()


def process_single(
    pdf_path: Path,
    output_path: Path,
    debug: bool,
    run_id: str,
) -> bool:
    orchestrator = PipelineOrchestrator(debug=debug, run_id=run_id)
    result = orchestrator.run(pdf_path, output_path)
    return result.success or result.partial


def main() -> int:
    args = parse_args()
    logger, run_id = setup_logging(debug=args.debug)

    input_path = args.input.resolve()
    output_path = args.output.resolve()

    if not input_path.exists():
        logger.error("Input not found: %s", input_path)
        return 1

    # Batch mode: input directory
    if input_path.is_dir():
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            logger.error("Batch mode requires output to be a directory")
            return 1

        pdfs = list_pdfs(input_path)
        if not pdfs:
            logger.error("No PDF files in %s", input_path)
            return 1

        failed = 0
        for pdf in pdfs:
            out_csv = output_csv_path(pdf, output_path)
            ok = process_single(pdf, out_csv, args.debug, run_id)
            if not ok:
                failed += 1
                logger.error("Failed: %s", pdf.name)

        if failed:
            logger.error("%d of %d files failed", failed, len(pdfs))
            return 1
        logger.info("Batch complete: %d files", len(pdfs))
        return 0

    # Single file mode
    if not is_pdf(input_path):
        logger.error("Input must be a .pdf file: %s", input_path)
        return 1

    out = output_path
    if output_path.suffix.lower() != ".csv":
        if output_path.is_dir() or not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
            out = output_path / f"{input_path.stem}.csv"
        else:
            out = output_path.with_suffix(".csv")

    orchestrator = PipelineOrchestrator(debug=args.debug, run_id=run_id)
    result = orchestrator.run(input_path, out)
    if result.success:
        logger.info("Wrote %d rows to %s", result.row_count, out)
        return 0
    if result.partial:
        logger.warning(
            "Partial CSV: %d of %d rows written to %s",
            result.row_count,
            result.rows_extracted,
            out,
        )
        return 0
    logger.error("Conversion failed with no exportable rows")
    return 1


if __name__ == "__main__":
    sys.exit(main())
