"""Tests for bank template detection."""

from parser.bank_detector import BankTemplateDetector
from parser.templates.monzo import MonzoTemplate
from parser.templates.hsbc import HsbcTemplate


def test_monzo_detect_score():
    t = MonzoTemplate()
    score = t.detect_score("Monzo Bank statement faster payment", [])
    assert score >= 0.5


def test_hsbc_detect_score():
    t = HsbcTemplate()
    score = t.detect_score("HSBC UK bank sort code paid out", [])
    assert score >= 0.5


def test_generic_low_score_without_keywords():
    from parser.templates.generic import GenericTemplate

    t = GenericTemplate()
    score = t.detect_score("random document", [])
    assert score < 0.5
