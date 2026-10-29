"""
Regressionstest Aehnlichkeit: Faellt ein Modellwechsel oder eine neue Normalisierung
auf das Messset, schlaegt das hier an.

Laedt das Einbettungsmodell (~1,5 GB RAM, einige Minuten auf zwei Kernen) und
braucht kein Qdrant. Deshalb langsam markiert und nicht in CI: CI sammelt nur
tests/unit und tests/integration, pytest.ini nur tests/unit. Den Aufbau des Messsets
(Labels, Split, Umfang) prueft tests/unit/test_aehnlichkeit_messset_aufbau.py ohne
Modell. Manuell:

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m pytest tests/regression -m langsam -v

Scheitert test_scores_wie_gemessen nach einem Modellwechsel, sind die Schwellen in
core/config.py neu zu messen - nicht nur aehnlichkeit_gemessen.py neu zu erzeugen.
"""

import pytest

from core.config import Settings
from tests.regression.aehnlichkeit_messen import (
    BEKANNTE_FEHLENTSCHEIDUNGEN,
    entscheidung,
    gemessen,
    knapp,
    scores,
)
from tests.regression.aehnlichkeit_paare import PAARE

pytestmark = pytest.mark.langsam

# Wie weit ein Score von der Messung abweichen darf (CPU/Bibliotheksversion).
TOLERANZ = 0.005


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_scores_wie_gemessen(paar):
    erwartet = gemessen(paar.id)
    assert scores()[paar.id] == pytest.approx(erwartet[:3], abs=TOLERANZ)


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_entscheidung_der_dublettenpruefung(paar):
    """Dieselbe Regel wie StatementService.add_statement / CommentaryService / GenericTextService."""
    settings = Settings()
    werte = scores()[paar.id]
    ergebnis = entscheidung(paar, werte, settings)
    if knapp(paar, werte, settings) or knapp(paar, gemessen(paar.id), settings):
        pytest.skip("Score direkt an der Schwelle, Entscheidung nicht stabil")

    assert ergebnis is gemessen(paar.id).gleich
    # Die Grundregeln unabhaengig von den gespeicherten Erwartungen:
    if paar.kategorie in "AB":
        assert ergebnis, "identisch/trivial abweichend muss als dasselbe gelten"
    if paar.label != "gleich" and paar.id not in BEKANNTE_FEHLENTSCHEIDUNGEN:
        assert not ergebnis, "andere Behauptung darf nie still zusammenfallen"


def test_bekannte_fehlentscheidungen_sind_noch_falsch():
    """Eine geloeste Fehlentscheidung faellt hier auf und wird aus der Liste genommen."""
    settings = Settings()
    nach_id = {p.id: p for p in PAARE}
    geloest = [
        pid
        for pid in BEKANNTE_FEHLENTSCHEIDUNGEN
        if not entscheidung(nach_id[pid], scores()[pid], settings)
        and not knapp(nach_id[pid], scores()[pid], settings)
    ]
    assert not geloest
