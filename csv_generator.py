"""Generate CSV output from validated rows."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

import config
from parser.templates.base import RawRow

logger = logging.getLogger(__name__)


def generate_csv(rows: list[RawRow], output_path: Path) -> None:
    """Write four-column CSV preserving transaction order."""
    data = {
        "Date": [],
        "Description": [],
        "Amount": [],
        "Balance": [],
    }
    for row in rows:
        data["Date"].append(row.date or "")
        data["Description"].append(row.description or "")
        data["Amount"].append(row.amount or "")
        data["Balance"].append(row.balance or "")

    df = pd.DataFrame(data, columns=config.OUTPUT_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Wrote %d rows to %s", len(rows), output_path)
