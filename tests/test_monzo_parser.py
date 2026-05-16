"""Tests for Monzo Business statement text parser."""

from parser.monzo_statement_parser import parse_monzo_lines


# pdfplumber-style jumbled order (description before date line)
SAMPLE_LINES = """
Date Description Amount Balance
Petaprint (Faster Payments) Reference:
01/05/2026 -79.65 2,148.39
33550
Petaprint (Faster Payments) Reference:
01/05/2026 -120.00 2,228.04
33547
Sykes Plumbing & Heating Ltd (Faster
01/05/2026 -90.00 2,348.04
Payments) Reference: 1053
Great Homes UK (Faster Payments)
30/04/2026 6500.00 6,527.04
Reference: 1 May expenses
""".strip().splitlines()


def test_monzo_multiline_descriptions():
    rows = parse_monzo_lines(SAMPLE_LINES)
    assert len(rows) >= 4
    descs = [r.description for r in rows]
    assert any("Petaprint" in d and "33550" in d for d in descs)
    assert any("Sykes Plumbing" in d for d in descs)
    assert any("Great Homes UK" in d for d in descs)


def test_monzo_amounts():
    rows = parse_monzo_lines(SAMPLE_LINES)
    pet = next(r for r in rows if "Petaprint" in r.description and r.amount == "-79.65")
    assert pet.balance == "2148.39"
    assert "33550" in pet.description


def test_monzo_deposit_positive_amount():
    rows = parse_monzo_lines(SAMPLE_LINES)
    dep = next(r for r in rows if "Great Homes UK" in r.description)
    assert dep.amount == "6500.00"
