"""Tests for validation engine."""

from parser.templates.base import RawRow
from parser.templates.generic import GenericTemplate
from validators.row_validator import ValidationEngine


def test_validate_good_rows():
    template = GenericTemplate()
    engine = ValidationEngine(template)
    rows = [
        RawRow(date="01/03/2024", description="Shop", amount="-5.00", balance="95.00"),
        RawRow(date="02/03/2024", description="Salary", amount="2500.00", balance="2595.00"),
    ]
    result = engine.validate(rows)
    assert len(result.rows) == 2
    assert not result.critical_errors


def test_remove_duplicates():
    template = GenericTemplate()
    engine = ValidationEngine(template)
    row = RawRow(date="01/03/2024", description="Shop", amount="-5.00", balance="95.00")
    result = engine.validate([row, row])
    assert len(result.rows) == 1
    assert result.removed_duplicates == 1


def test_invalid_amount_critical():
    template = GenericTemplate()
    engine = ValidationEngine(template)
    rows = [RawRow(date="01/03/2024", description="Bad", amount="notanamount", balance="")]
    result = engine.validate(rows)
    assert result.critical_errors
