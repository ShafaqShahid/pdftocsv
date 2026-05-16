"""Camelot-based table extraction."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import config
from parser.templates.base import BankTemplate, RawRow

logger = logging.getLogger(__name__)


def extract_with_camelot(
    pdf_path: Path,
    template: BankTemplate,
    flavor: str = "lattice",
    debug: bool = False,
) -> list[RawRow]:
    """Extract tables using camelot (lattice or stream)."""
    rows: list[RawRow] = []
    try:
        import camelot
    except ImportError:
        logger.warning("camelot not installed")
        return rows

    try:
        tables = camelot.read_pdf(
            str(pdf_path),
            pages="all",
            flavor=flavor,
        )
    except Exception as e:
        logger.warning("Camelot %s failed: %s", flavor, e)
        return rows

    for table in tables:
        page = int(table.page)
        df = table.df
        for _, series in df.iterrows():
            cells = [str(v).strip() if v else "" for v in series.tolist()]
            norm = template.normalize_row(cells)
            if norm:
                rows.append(
                    RawRow(
                        date=norm.date,
                        description=norm.description,
                        amount=norm.amount,
                        balance=norm.balance,
                        page=page,
                        source=f"camelot_{flavor}",
                        raw_cells=cells,
                    )
                )

    if debug and config.DEBUG_SAVE_INTERMEDIATE:
        _save_debug(pdf_path, flavor, len(rows))

    logger.info("Camelot %s extracted %d rows from %s", flavor, len(rows), pdf_path.name)
    return rows


def _save_debug(pdf_path: Path, flavor: str, count: int) -> None:
    config.DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DEBUG_DIR / f"{pdf_path.stem}_camelot_{flavor}.json"
    path.write_text(json.dumps({"row_count": count}), encoding="utf-8")
