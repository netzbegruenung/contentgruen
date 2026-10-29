"""
Verbot der App-Datenbank in Unit-Tests (#460), eingebunden in tests/unit/conftest.py.

``get_app_database()`` baut ohne Adresse eine Verbindung zum PostgreSQL aus den
Settings: auf der Dev-VM der laufende Dev-Stack, in der CI nichts. Ein Unit-Test,
der eine Abhaengigkeit nicht ersetzt hat, lief deshalb lokal gruen und in der CI rot.
Das Verbot macht daraus ueberall denselben Fehler. Eine ``AppDatabase`` mit eigener
Adresse (etwa ``sqlite://``) bleibt erlaubt.

Faengt der Code die Ausnahme ab, scheitert der Test trotzdem
(``pytest_runtest_makereport``): Sonst liefe er in der CI still an einer anderen
Stelle weiter als lokal.

Grenze: Gesperrt ist nur ``AppDatabase()`` ohne Adresse, also der Weg ueber
``get_app_database()``. Wer die Adresse aus den Settings selbst uebergibt, kommt
durch; App-Code tut das nicht.
"""

import pytest

from infrastructure.database import connection
from infrastructure.database.connection import AppDatabase

MELDUNG = (
    "Unit-Test oeffnet die App-Datenbank (get_app_database ohne Adresse). "
    "Abhaengigkeit ueberschreiben oder das Repository ersetzen, siehe "
    "tests/conftest.py (anzeigenamen_ohne_datenbank)."
)


class AppDatenbankVerboten(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def app_datenbank_versuche(monkeypatch):
    """Verbietet die App-Datenbank; liefert die Versuche im laufenden Test.

    Wer einen Versuch erwartet, leert die Liste danach.
    """
    versuche = []
    original = AppDatabase.__init__

    def verboten(self, database_url=None):
        if database_url is None:
            versuche.append(MELDUNG)
            raise AppDatenbankVerboten(MELDUNG)
        original(self, database_url)

    monkeypatch.setattr(AppDatabase, "__init__", verboten)
    monkeypatch.setattr(connection, "_app_db", None)
    yield versuche


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    bericht = yield
    versuche = getattr(item, "funcargs", {}).get(app_datenbank_versuche.__name__)
    if bericht.when == "call" and bericht.passed and versuche:
        bericht.outcome = "failed"
        bericht.longrepr = f"{MELDUNG} Die Ausnahme wurde abgefangen."
    return bericht
