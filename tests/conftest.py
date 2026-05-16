"""Pytest fixtures."""

from __future__ import annotations

import pytest

from parser.templates.generic import GenericTemplate
from parser.templates.monzo import MonzoTemplate


@pytest.fixture
def generic_template() -> GenericTemplate:
    return GenericTemplate()


@pytest.fixture
def monzo_template() -> MonzoTemplate:
    return MonzoTemplate()
