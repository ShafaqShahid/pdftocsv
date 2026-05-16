"""Tests for regex line parsing logic."""

from parser.regex_extractor import _parse_text_lines
from parser.templates.generic import GenericTemplate


def test_parse_multiline_description():
    template = GenericTemplate()
    text = """01/03/2024 Heating And Water Solutions (Faster
Payments) Reference: 6057 -150.00 1,234.56
02/03/2024 Salary Payment 2,500.00 3,734.56"""
    rows = _parse_text_lines(text, 1, template, "uk")
    assert len(rows) >= 2
    assert "Heating" in rows[0].description or "Faster" in rows[0].description


def test_skip_footer_line():
    template = GenericTemplate()
    text = "01/03/2024 Shop -5.00 95.00\nPage 2 of 5"
    rows = _parse_text_lines(text, 1, template, "uk")
    assert len(rows) == 1
