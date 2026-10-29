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
from tests.regression.aehnlichkeit_gemessen import GEMESSEN
from tests.regression.aehnlichkeit_messen import entscheidung, scores
from tests.regression.aehnlichkeit_paare import PAARE

pytestmark = pytest.mark.langsam

# Wie weit ein Score von der Messung abweichen darf (CPU/Bibliotheksversion).
TOLERANZ = 0.005

# Paare, bei denen die heutige Dublettenpruefung (Kosinus + Schwelle) eine andere
# Behauptung als dieselbe nimmt. Bekannt und gewollt sichtbar: Diese Faelle
# soll die NLI-Stufe (#387) abfangen. Wer hier ein Paar entfernt, hat es geloest.
# fmt: off
BEKANNTE_FEHLENTSCHEIDUNGEN = frozenset({
    # Aussagen (49): still als dieselbe Aussage wiederverwendet
    "VB05", "VB09", "WI07", "BS09", "WP04", "WP07", "TL06", "TL07", "EA04", "EA05",
    "EA06", "EA07", "EA08", "FL04", "FL09", "HZ04", "HZ08", "HZ09", "EU06", "DB07",
    "KW08", "SP07", "LR04", "CO05", "RW05", "RW06", "WS08", "IN05", "IN06", "IN08",
    "WA06", "WA10", "DT05", "BI04", "BI06", "FB03", "FB04", "FB05", "FB06", "AK04",
    "AK07", "AK08", "MO06", "FW03", "FW04", "FW05", "FW06", "FW08", "WO08",
    # Hintergrundinfos (13): andere Zahl oder Verneinung im sonst gleichen
    # Text, als Dublette angeboten
    "HK03", "HK04", "HA04", "HA05", "HA06", "HU04", "HU05", "HJ03", "HJ04", "HT03",
    "HT04", "HG03", "HG04",
})
# fmt: on


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_scores_wie_gemessen(paar):
    qq, pp, qp, *_ = GEMESSEN[paar.id]
    assert scores()[paar.id] == pytest.approx((qq, pp, qp), abs=TOLERANZ)


@pytest.mark.parametrize("paar", PAARE, ids=[p.id for p in PAARE])
def test_entscheidung_der_dublettenpruefung(paar):
    """Dieselbe Regel wie StatementService.add_statement / CommentaryService / GenericTextService."""
    qq, pp, _ = scores()[paar.id]
    ergebnis = entscheidung(paar, qq, pp, Settings())

    assert ergebnis is GEMESSEN[paar.id][3]
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
        if not entscheidung(nach_id[pid], *scores()[pid][:2], settings)
    ]
    assert not geloest
