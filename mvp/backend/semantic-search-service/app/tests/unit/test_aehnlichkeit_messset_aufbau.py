"""
Aufbau des Messsets (tests/regression/aehnlichkeit_paare.py) ohne Einbettungsmodell:
Labels, Umfang, fester Train/Test-Split und dass die gespeicherten Messwerte zu den
Texten passen. Die Scores selbst prueft tests/regression (langsam, nicht in CI).
"""

from collections import Counter

import pytest

from tests.regression.aehnlichkeit_gemessen import GEMESSEN
from tests.regression.aehnlichkeit_messen import (
    PRUEFUNG_JE_ART,
    fingerabdruck,
    gemessen,
)
from tests.regression.aehnlichkeit_paare import (
    LABELS,
    MINIMALPAAR_PHAENOMENE,
    PAARE,
    PHAENOMENE,
    TEST_GRUPPEN,
)
from utils.text_normalisierung import text_normalisiert

AUSSAGEN = [p for p in PAARE if p.art == "aussage"]


def test_ids_eindeutig():
    doppelt = [i for i, n in Counter(p.id for p in PAARE).items() if n > 1]
    assert not doppelt


def test_jedes_paar_hat_label_und_phaenomen():
    assert all(p.label in LABELS for p in PAARE)
    assert all(p.phaenomen in PHAENOMENE for p in PAARE)
    assert {p.art for p in PAARE} == set(PRUEFUNG_JE_ART)


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_kategorie_passt_zum_label(paar):
    erlaubt = {"A": {"gleich"}, "B": {"gleich"}, "C": {"gleich"}}
    erlaubt |= {"D": {"verwandt", "widerspricht"}, "E": {"fremd"}}
    assert paar.label in erlaubt[paar.kategorie]


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_kandidat_weicht_vom_bestand_ab_ausser_bei_identisch(paar):
    """Abgeleitete Varianten (replace, lower, ...) duerfen nicht still zum A-Paar werden."""
    assert (paar.kandidat == paar.bestand) is (paar.kategorie == "A")


def test_umfang_der_aussage_paare():
    assert len(AUSSAGEN) >= 300
    minimal = Counter(
        p.phaenomen for p in AUSSAGEN if p.phaenomen in MINIMALPAAR_PHAENOMENE
    )
    assert sum(minimal.values()) >= 100
    assert set(minimal) == MINIMALPAAR_PHAENOMENE


def test_harte_faelle_enthalten():
    phaenomene = Counter(p.phaenomen for p in AUSSAGEN)
    for noetig in ("frage", "tippfehler", "wortstellung", "skopus", "mehrfachthema"):
        assert phaenomene[noetig] > 0, noetig
    # Frage gegen Behauptung ist nie dieselbe Behauptung (MESSSET.md, Grenzfaelle).
    assert {p.label for p in AUSSAGEN if p.phaenomen == "frage"} == {"verwandt"}


def test_mindestens_20_hintergrundinfo_paare():
    assert sum(p.art == "hintergrundinfo" for p in PAARE) >= 20


def test_split_fest_nach_gruppe():
    gruppen = {p.gruppe for p in PAARE}
    assert TEST_GRUPPEN <= gruppen, "Test-Gruppe ohne Paare"
    assert "alt" not in TEST_GRUPPEN, "an den alten Paaren sind die Schwellen gesetzt"
    for teil in ("train", "test"):
        labels = {p.label for p in AUSSAGEN if p.teil == teil}
        assert labels == set(LABELS), teil


def test_kein_text_in_train_und_test():
    def texte(teil):
        return {
            text_normalisiert(t)
            for p in PAARE
            if p.teil == teil
            for t in (p.kandidat, p.bestand)
        }

    assert not texte("train") & texte("test")


def test_gemessen_passt_zu_den_paaren():
    """Neue oder umnummerierte Paare: aehnlichkeit_messen.py --schreiben laufen lassen."""
    assert set(GEMESSEN) == {p.id for p in PAARE}
    veraltet = [p.id for p in PAARE if gemessen(p.id).fingerabdruck != fingerabdruck(p)]
    assert not veraltet
