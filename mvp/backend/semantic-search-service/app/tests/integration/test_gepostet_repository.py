"""
Rueckmeldung "Gepostet?" (#643) gegen ein echtes PostgreSQL: ein Pruefwert zaehlt je
Woche einmal, vergangene Wochen werden zur Zahl verdichtet und ihre Pruefwerte
geloescht. Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

from datetime import date

import pytest
from sqlalchemy import text

from repositories.gepostet_repository import GepostetRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration

VORIGE = date(2026, 11, 2)
DIESE = date(2026, 11, 9)


def _zeilen(datenbank, tabelle: str) -> int:  # noqa: F811
    with datenbank.get_session() as c:
        return c.execute(text(f"SELECT count(*) FROM {tabelle}")).scalar()


class TestGepostet:
    def test_derselbe_pruefwert_zaehlt_einmal(self, datenbank):  # noqa: F811
        repo = GepostetRepository(datenbank)

        assert repo.melden("a" * 64, DIESE) == 1
        assert repo.melden("a" * 64, DIESE) == 1
        assert repo.melden("b" * 64, DIESE) == 2
        assert repo.anzahl(DIESE) == 2

    def test_vergangene_woche_wird_zur_zahl(self, datenbank):  # noqa: F811
        repo = GepostetRepository(datenbank)
        repo.melden("a" * 64, VORIGE)
        repo.melden("b" * 64, VORIGE)

        assert repo.melden("c" * 64, DIESE) == 1

        assert _zeilen(datenbank, "gepostet_pruefwerte") == 1
        assert repo.wochen(VORIGE, DIESE) == {VORIGE: 2, DIESE: 1}

    def test_spaeter_eintreffende_meldung_der_vorigen_woche_zaehlt_dazu(
        self, datenbank  # noqa: F811
    ):
        repo = GepostetRepository(datenbank)
        repo.melden("a" * 64, VORIGE)
        repo.wochen(VORIGE, DIESE)
        # Eine Anfrage, die vor dem Wochenwechsel begann.
        repo.melden("b" * 64, VORIGE)

        assert repo.wochen(VORIGE, DIESE) == {VORIGE: 2}
        assert _zeilen(datenbank, "gepostet_pruefwerte") == 0

    def test_taeglicher_lauf_verdichtet_ohne_neue_meldung(
        self, datenbank
    ):  # noqa: F811
        repo = GepostetRepository(datenbank)
        repo.melden("a" * 64, VORIGE)
        repo.melden("b" * 64, DIESE)

        repo.vergangene_wochen_verdichten(heute=date(2026, 11, 11))

        assert _zeilen(datenbank, "gepostet_pruefwerte") == 1
        with datenbank.get_session() as c:
            assert (
                c.execute(
                    text("SELECT personen FROM gepostet_wochen WHERE woche = :w"),
                    {"w": VORIGE},
                ).scalar()
                == 1
            )

    def test_wochen_ab_von(self, datenbank):  # noqa: F811
        repo = GepostetRepository(datenbank)
        repo.melden("a" * 64, date(2026, 10, 26))
        repo.melden("b" * 64, VORIGE)

        assert repo.wochen(VORIGE, DIESE) == {VORIGE: 1}
