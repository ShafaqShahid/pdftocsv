"""Tests for extraction quality scoring."""

from parser.extractor import quality_score
from parser.templates.base import RawRow
from parser.templates.generic import GenericTemplate


def test_quality_score_all_valid():
    template = GenericTemplate()
    rows = [
        RawRow(date="01/03/2024", description="A", amount="-1.00", balance=""),
        RawRow(date="02/03/2024", description="B", amount="2.00", balance=""),
    ]
    assert quality_score(rows, template) == 1.0


def test_quality_score_empty():
    template = GenericTemplate()
    assert quality_score([], template) == 0.0
