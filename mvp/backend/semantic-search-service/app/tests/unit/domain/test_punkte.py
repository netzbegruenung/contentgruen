"""
Punkte in drei Stufen (ADR 0004, #352): kleine, je Tag gedeckelte Punkte fuers Tun,
mehr fuer abgeschlossene Quests, die grossen fuer die Wirkung bei anderen.
"""

from datetime import date

from domain.punkte import Punktegewichte, Wirkungsdaten, punkte_berechnen

GEWICHTE = Punktegewichte(
    nutzung=10,
    zustimmung=5,
    beitrag=1,
    einwurf_ausformuliert=1,
    deckel_tun_je_tag=3,
    quest=4,
    deckel_quests_je_tag=8,
)
MONTAG = date(2026, 10, 26)
DIENSTAG = date(2026, 10, 27)


def test_punkte_berechnen_ohne_daten_null():
    stand = punkte_berechnen(Wirkungsdaten(), GEWICHTE)

    assert (stand.tun, stand.quests, stand.wirkung, stand.gesamt) == (0, 0, 0, 0)


def test_punkte_berechnen_wirkung_aus_nutzung_und_zustimmung():
    stand = punkte_berechnen(Wirkungsdaten(nutzungen=3, zustimmungen=2), GEWICHTE)

    assert stand.wirkung == 40
    assert stand.gesamt == 40


def test_punkte_berechnen_tun_je_tag_gedeckelt():
    daten = Wirkungsdaten(
        beitraege_je_tag={MONTAG: 5, DIENSTAG: 1},
        einwuerfe_ausformuliert_je_tag={MONTAG: 1, DIENSTAG: 1},
    )

    stand = punkte_berechnen(daten, GEWICHTE)

    # Montag 6, gedeckelt auf 3; Dienstag 2.
    assert stand.tun == 5


def test_punkte_berechnen_quests_je_tag_gedeckelt():
    daten = Wirkungsdaten(quests_je_tag={MONTAG: 3, DIENSTAG: 1})

    stand = punkte_berechnen(daten, GEWICHTE)

    assert stand.quests == 12


def test_punkte_berechnen_gesamt_ist_summe_der_stufen():
    daten = Wirkungsdaten(
        nutzungen=1,
        zustimmungen=1,
        beitraege_je_tag={MONTAG: 1},
        quests_je_tag={MONTAG: 1},
    )

    stand = punkte_berechnen(daten, GEWICHTE)

    assert stand.gesamt == 15 + 1 + 4
