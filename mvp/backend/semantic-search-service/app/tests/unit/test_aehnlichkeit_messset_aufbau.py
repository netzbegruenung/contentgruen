"""
Aufbau des Messsets (tests/regression/aehnlichkeit_paare.py) ohne Einbettungsmodell:
Labels, Umfang, fester Train/Test-Split und dass die gespeicherten Messwerte zu den
Texten passen. Die Scores selbst prueft tests/regression (langsam, nicht in CI).
"""

from collections import Counter
from pathlib import Path

import pytest

from core.config import Settings
from tests.regression.aehnlichkeit_gemessen import GEMESSEN
from tests.regression.aehnlichkeit_messen import (
    BEKANNTE_FEHLENTSCHEIDUNGEN,
    PRUEFUNG_JE_ART,
    auswertung,
    entscheidung,
    fingerabdruck,
    gemessen,
)
from tests.regression.aehnlichkeit_paare import (
    LABELS,
    MINIMALPAAR_PHAENOMENE,
    PAARE,
    PHAENOMENE,
    QUELLEN,
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


def test_quelle_aus_den_erlaubten_in_fester_reihenfolge():
    erlaubt = {"+".join(q for q in QUELLEN if q in teile) for teile in _teilmengen()}
    assert {p.quelle for p in PAARE} <= erlaubt


def _teilmengen():
    return [
        {q for i, q in enumerate(QUELLEN) if maske >> i & 1}
        for maske in range(1, 2 ** len(QUELLEN))
    ]


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_kategorie_passt_zum_label(paar):
    """Bei den neuen Gruppen leitet _kategorie() die Kategorie aus dem Label ab; echt
    geprueft wird hier der Altbestand, dessen Kategorie von Hand steht."""
    erlaubt = {"A": {"gleich"}, "B": {"gleich"}, "C": {"gleich"}}
    erlaubt |= {"D": {"verwandt", "widerspricht"}, "E": {"fremd"}}
    assert paar.label in erlaubt[paar.kategorie]


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_kandidat_weicht_vom_bestand_ab_ausser_bei_identisch(paar):
    """Abgeleitete Varianten (replace, lower, ...) duerfen nicht still zum A-Paar werden."""
    assert (paar.kandidat == paar.bestand) is (paar.kategorie == "A")


def test_umfang_der_aussage_paare():
    assert len(AUSSAGEN) >= 300
    # Harte Negative: Minimalpaare mit anderer Behauptung (MESSSET.md, Phänomen).
    minimal = Counter(
        p.phaenomen
        for p in AUSSAGEN
        if p.phaenomen in MINIMALPAAR_PHAENOMENE and p.label != "gleich"
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


def test_gespeicherte_entscheidung_passt_zu_den_scores():
    """Was aehnlichkeit_gemessen.py als Entscheidung speichert, folgt aus den
    gespeicherten Scores und den Schwellen in core/config.py. Faellt nach einer
    Schwellenaenderung auf: dann neu messen."""
    settings = Settings()
    abweichend = [
        p.id
        for p in PAARE
        if entscheidung(p, gemessen(p.id), settings) is not gemessen(p.id).gleich
    ]
    assert not abweichend


def test_bekannte_fehlentscheidungen_passen_zur_messung():
    fehlentscheidungen = {
        p.id for p in PAARE if p.label != "gleich" and gemessen(p.id).gleich
    }
    assert BEKANNTE_FEHLENTSCHEIDUNGEN == fehlentscheidungen


def test_messset_md_zeigt_die_gespeicherte_messung():
    """Die Tabellen in MESSSET.md sind die Ausgabe von aehnlichkeit_messen.py."""
    doku = Path(__file__).parents[1] / "regression" / "MESSSET.md"
    messungen = {p.id: gemessen(p.id) for p in PAARE}
    assert auswertung(messungen, Settings()) in doku.read_text(encoding="utf-8")
