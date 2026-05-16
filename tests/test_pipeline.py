"""End-to-end pipeline tests with mocked components."""

from pathlib import Path

import pandas as pd

from csv_generator import generate_csv
from parser.templates.base import RawRow
from validators.row_validator import ValidationEngine
from parser.templates.generic import GenericTemplate


def test_csv_generator_columns(tmp_path: Path):
    rows = [
        RawRow(date="01/03/2024", description="Test, with comma", amount="-10.00", balance="90.00"),
    ]
    out = tmp_path / "out.csv"
    generate_csv(rows, out)
    df = pd.read_csv(out)
    assert list(df.columns) == ["Date", "Description", "Amount", "Balance"]
    assert df.iloc[0]["Description"] == "Test, with comma"


def test_validation_pipeline(tmp_path: Path):
    template = GenericTemplate()
    rows = [
        RawRow(date="01/03/2024", description="A", amount="-1.00", balance="99.00"),
        RawRow(date="02/03/2024", description="B", amount="2.00", balance="101.00"),
    ]
    result = ValidationEngine(template).validate(rows)
    out = tmp_path / "test.csv"
    generate_csv(result.rows, out)
    assert out.exists()
    assert len(pd.read_csv(out)) == 2
