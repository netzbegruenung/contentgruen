"""
Rueckmeldung "Gepostet?" (#643): eine Person zaehlt je Kalenderwoche einmal, ihr
Pruefwert verraet sie nicht und wechselt mit der Woche.
"""

from datetime import date
from typing import Dict

import pytest

from services import gepostet_service as modul
from services.gepostet_service import (
    GepostetService,
    GepostetWoche,
    gepostet_pruefwert,
)

MONTAG = date(2026, 11, 9)
SONNTAG = date(2026, 11, 15)


@pytest.fixture(autouse=True)
def frischer_wochenschluessel(monkeypatch):
    """Jeder Test mit eigenem Schluessel: Ein Wochenwechsel in einem Test wirkt nicht weiter."""
    monkeypatch.setattr(modul, "_WOCHENSCHLUESSEL", modul.Tagesschluessel())


class Speicher:
    """Wie das Repository, im Speicher: Pruefwerte je Woche."""

    def __init__(self):
        self.werte: Dict[date, set] = {}

    def melden(self, pruefwert: str, woche: date) -> int:
        self.werte.setdefault(woche, set()).add(pruefwert)
        return len(self.werte[woche])

    def anzahl(self, woche: date) -> int:
        return len(self.werte.get(woche, set()))

    def wochen(self, von: date, laufende: date) -> Dict[date, int]:
        return {w: len(v) for w, v in self.werte.items() if von <= w <= laufende}


def test_zweimal_in_derselben_woche_zaehlt_einmal():
    speicher = Speicher()
    dienst = GepostetService(speicher)

    assert dienst.melden("kim-1", heute=MONTAG) == 1
    assert dienst.melden("kim-1", heute=SONNTAG) == 1
    assert dienst.melden("bo-2", heute=SONNTAG) == 2
    assert dienst.diese_woche(heute=SONNTAG) == 2
    assert list(speicher.werte) == [MONTAG]


def test_pruefwert_ohne_kennung_und_je_woche_neu():
    diese = gepostet_pruefwert("kim-1", MONTAG)

    assert "kim-1" not in diese
    assert len(diese) == 64
    assert gepostet_pruefwert("kim-1", MONTAG) == diese
    assert gepostet_pruefwert("bo-2", MONTAG) != diese
    assert gepostet_pruefwert("kim-1", date(2026, 11, 16)) != diese


def test_neue_woche_beginnt_bei_null():
    dienst = GepostetService(Speicher())
    dienst.melden("kim-1", heute=SONNTAG)

    assert dienst.melden("kim-1", heute=date(2026, 11, 16)) == 1
    assert dienst.diese_woche(heute=date(2026, 11, 17)) == 1


def test_wochen_mit_nullen_die_laufende_zuletzt():
    dienst = GepostetService(Speicher())
    dienst.melden("kim-1", heute=date(2026, 11, 3))
    dienst.melden("bo-2", heute=date(2026, 11, 4))

    assert dienst.wochen(3, heute=date(2026, 11, 12)) == [
        GepostetWoche(date(2026, 10, 26), 0),
        GepostetWoche(date(2026, 11, 2), 2),
        GepostetWoche(MONTAG, 0),
    ]
