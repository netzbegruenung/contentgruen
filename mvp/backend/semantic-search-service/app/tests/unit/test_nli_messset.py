"""
Die NLI-Stufe (#387) am Messset, ohne Modell: Die gespeicherten Urteile
(tests/regression/nli_gemessen.py) passen zu den Texten, und die Regel mit den
Schwellen aus core/config.py haelt die Grundregeln ein. Faellt nach einer
Schwellen- oder Regelaenderung auf. Die Urteile selbst prueft tests/regression
(langsam, nicht in CI).
"""

from pathlib import Path

import pytest

from core.config import Settings
from tests.regression.aehnlichkeit_messen import fingerabdruck, gemessen
from tests.regression.nli_gemessen import NLI_GEMESSEN
from tests.regression.nli_messen import (
    HARTE_FAELLE,
    NLI_PAARE,
    auswertung,
    entscheidung_nli,
    urteil,
)

SETTINGS = Settings()


def test_jedes_aussage_paar_ist_gemessen():
    assert set(NLI_GEMESSEN) == {p.id for p in NLI_PAARE}
    veraltet = [p.id for p in NLI_PAARE if NLI_GEMESSEN[p.id][4] != fingerabdruck(p)]
    assert not veraltet


@pytest.mark.parametrize("paar", NLI_PAARE, ids=[p.id for p in NLI_PAARE])
def test_grundregeln(paar):
    dieselbe = entscheidung_nli(paar, urteil(paar.id), SETTINGS)
    if paar.kategorie in "AB" and paar.label == "gleich":
        assert dieselbe, "identisch/trivial abweichend muss als dieselbe gelten"
    if paar.label != "gleich":
        assert not dieselbe, "andere Behauptung darf nie still zusammenfallen"


@pytest.mark.parametrize("paar_id", HARTE_FAELLE)
def test_gegenteile_und_fragen_nie_dieselbe(paar_id):
    paar = next(p for p in NLI_PAARE if p.id == paar_id)
    assert not entscheidung_nli(paar, urteil(paar_id), SETTINGS)


def test_untergrenze_liegt_unter_allen_gleichen_aussagen():
    """Sonst sieht das Modell eine Umformulierung nie (MESSSET.md, NLI-Stufe)."""
    niedrigste = min(gemessen(p.id).qq for p in NLI_PAARE if p.label == "gleich")
    assert SETTINGS.nli_kandidaten_ab < niedrigste


def test_nli_erkennt_mehr_gleiche_als_die_schwelle():
    def erkannt(teil, mit_nli):
        return sum(
            (
                entscheidung_nli(p, urteil(p.id), SETTINGS)
                if mit_nli
                else gemessen(p.id).gleich
            )
            for p in NLI_PAARE
            if p.label == "gleich" and p.teil == teil
        )

    assert erkannt("test", True) > erkannt("test", False)


def test_messset_md_zeigt_die_gespeicherte_messung():
    """Die Tabellen im Abschnitt NLI-Stufe sind die Ausgabe von nli_messen.py."""
    doku = Path(__file__).parents[1] / "regression" / "MESSSET.md"
    urteile = {p.id: urteil(p.id) for p in NLI_PAARE}
    assert auswertung(urteile, SETTINGS) in doku.read_text(encoding="utf-8")
