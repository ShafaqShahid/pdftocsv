"""Tests for header/footer filtering."""

from parser.header_footer import HeaderFooterCleaner
from parser.templates.base import RawRow


def test_remove_page_footer():
    cleaner = HeaderFooterCleaner()
    rows = [
        RawRow(date="01/03/2024", description="Shop", amount="-5.00", balance="95.00"),
        RawRow(date="", description="Page 2 of 5", amount="", balance=""),
        RawRow(date="Date", description="Description", amount="Amount", balance="Balance"),
    ]
    result = cleaner.clean(rows)
    assert len(result) == 1
    assert result[0].description == "Shop"


def test_remove_footer_keyword():
    cleaner = HeaderFooterCleaner()
    rows = [
        RawRow(date="", description="Total payments this period", amount="", balance=""),
        RawRow(date="02/03/2024", description="Transfer", amount="100.00", balance="200.00"),
    ]
    result = cleaner.clean(rows)
    assert len(result) == 1
