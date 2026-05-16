"""Bank-specific statement templates."""

from parser.templates.base import BankTemplate, RawRow
from parser.templates.generic import GenericTemplate
from parser.templates.monzo import MonzoTemplate
from parser.templates.hsbc import HsbcTemplate
from parser.templates.barclays import BarclaysTemplate

__all__ = [
    "BankTemplate",
    "RawRow",
    "GenericTemplate",
    "MonzoTemplate",
    "HsbcTemplate",
    "BarclaysTemplate",
]
