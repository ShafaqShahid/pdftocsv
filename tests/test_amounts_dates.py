"""Tests for amount and date utilities."""

from decimal import Decimal

from utils.amounts import parse_amount, format_amount
from utils.dates import parse_date, normalize_date_display, line_starts_with_date


def test_parse_amount_with_commas():
    assert parse_amount("1,234.56") == Decimal("1234.56")


def test_parse_amount_negative_parentheses():
    assert parse_amount("(150.00)") == Decimal("-150.00")


def test_parse_amount_pound_symbol():
    assert parse_amount("£-50.00") == Decimal("-50.00")


def test_format_amount():
    assert format_amount(Decimal("-150")) == "-150.00"


def test_parse_date_uk():
    dt = parse_date("01/03/2024", "uk")
    assert dt is not None
    assert dt.day == 1
    assert dt.month == 3


def test_parse_date_text_month():
    dt = parse_date("15 Jan 2024", "uk")
    assert dt is not None
    assert dt.month == 1


def test_normalize_date_display():
    assert normalize_date_display("01/03/2024", "uk") == "01/03/2024"


def test_line_starts_with_date():
    assert line_starts_with_date("01/03/2024 Payment", "uk")
    assert not line_starts_with_date("Payment 01/03/2024", "uk")
