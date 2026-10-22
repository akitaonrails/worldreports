"""Make the repository root importable, and offer the five countries.

Tests run from the root — `python3 -m pytest` — so `core` and the
`countries/` tree resolve the same way they do for the build.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.country import Country  # noqa: E402


def pytest_generate_tests(metafunc):
    """Any test taking a `country` argument runs once per country.

    Country-generic tests are written once and applied to all five, which
    is the point of the monorepo: a rule that holds for France has to hold
    for a country added next year without anyone remembering to copy the
    test.
    """
    if "country" in metafunc.fixturenames:
        countries = Country.all()
        metafunc.parametrize("country", countries,
                             ids=[c.slug for c in countries])


@pytest.fixture(scope="session")
def countries():
    return Country.all()


@pytest.fixture(scope="session")
def root():
    return ROOT
