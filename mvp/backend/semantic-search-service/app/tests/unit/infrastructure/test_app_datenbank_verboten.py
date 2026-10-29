"""
Unit-Tests oeffnen keine App-Datenbank (#460).

Ohne Verbot verband sich ein Unit-Test, der eine Abhaengigkeit nicht ersetzt hatte,
still mit dem PostgreSQL aus den Settings: lokal der laufende Dev-Stack, in der CI
nichts. Das Verbot (``tests/fixtures/ohne_app_datenbank.py``) macht daraus einen Fehler, auch
wenn der Code die Ausnahme abfaengt.
"""

import pytest

from infrastructure.database.connection import AppDatabase, get_app_database
from tests.fixtures.ohne_app_datenbank import AppDatenbankVerboten


@pytest.mark.unit
def test_get_app_database_ist_verboten(app_datenbank_verboten):
    with pytest.raises(AppDatenbankVerboten):
        get_app_database()
    # Erwartet: den Versuch vergessen, sonst schlaegt das Verbot diesen Test fehl.
    app_datenbank_verboten.clear()


@pytest.mark.unit
def test_datenbank_mit_eigener_adresse_bleibt_erlaubt():
    assert AppDatabase("sqlite://").database_url == "sqlite://"


@pytest.mark.unit
def test_abgefangener_versuch_laesst_den_test_scheitern(pytester):
    pytester.makeconftest(
        "from tests.fixtures.ohne_app_datenbank import (  # noqa: F401\n"
        "    app_datenbank_verboten,\n"
        "    pytest_runtest_makereport,\n"
        ")\n"
    )
    pytester.makepyfile(
        """
        from infrastructure.database.connection import get_app_database

        def test_schluckt_den_fehler():
            try:
                get_app_database()
            except Exception:
                pass
        """
    )
    ergebnis = pytester.runpytest_inprocess("-p", "no:cacheprovider")
    ergebnis.assert_outcomes(failed=1)
    ergebnis.stdout.fnmatch_lines(["*App-Datenbank*"])
