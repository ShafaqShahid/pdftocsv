"""Tests for multi-line row reconstruction."""

from parser.row_reconstructor import RowReconstructor
from parser.templates.base import RawRow
from parser.templates.generic import GenericTemplate


def test_merge_wrapped_description():
    template = GenericTemplate()
    recon = RowReconstructor(template)
    rows = [
        RawRow(
            date="01/03/2024",
            description="Heating And Water Solutions (Faster",
            amount="-150.00",
            balance="1234.56",
        ),
        RawRow(
            date="",
            description="Payments) Reference: 6057",
            amount="",
            balance="",
        ),
    ]
    result = recon.reconstruct(rows)
    assert len(result) == 1
    assert "Faster" in result[0].description
    assert "Payments)" in result[0].description
    assert "6057" in result[0].description


def test_two_separate_transactions():
    template = GenericTemplate()
    recon = RowReconstructor(template)
    rows = [
        RawRow(date="01/03/2024", description="Payment A", amount="-10.00", balance="100.00"),
        RawRow(date="02/03/2024", description="Payment B", amount="-20.00", balance="80.00"),
    ]
    result = recon.reconstruct(rows)
    assert len(result) == 2
