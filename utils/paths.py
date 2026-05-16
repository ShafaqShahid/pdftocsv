"""Path helpers for CLI batch mode."""

from __future__ import annotations

from pathlib import Path


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf" and path.is_file()


def list_pdfs(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if is_pdf(p))


def output_csv_path(input_pdf: Path, output: Path) -> Path:
    """Resolve output CSV path for a single PDF."""
    if output.suffix.lower() == ".csv":
        return output
    output.mkdir(parents=True, exist_ok=True)
    return output / f"{input_pdf.stem}.csv"
