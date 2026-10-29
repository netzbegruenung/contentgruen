"""Unit-Tests oeffnen keine App-Datenbank (#460): tests/fixtures/ohne_app_datenbank.py."""

from tests.fixtures.ohne_app_datenbank import (  # noqa: F401 - Fixture und Hook
    app_datenbank_verboten,
    pytest_runtest_makereport,
)
