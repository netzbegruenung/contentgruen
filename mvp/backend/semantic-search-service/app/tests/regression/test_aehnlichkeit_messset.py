"""
Regressionstest Aehnlichkeit: Faellt ein Modellwechsel oder eine neue Normalisierung
auf das Messset, schlaegt das hier an.

Laedt das Einbettungsmodell (~1,5 GB RAM, gut eine Minute auf zwei Kernen) und
braucht kein Qdrant. Deshalb langsam markiert und nicht in CI: CI sammelt nur
tests/unit und tests/integration, pytest.ini nur tests/unit. Manuell:

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m pytest tests/regression -m langsam -v

Scheitert test_scores_wie_gemessen nach einem Modellwechsel, sind die Schwellen in
core/config.py neu zu messen - nicht nur die erwarteten Werte zu ersetzen.
"""

from functools import lru_cache

import numpy as np
import pytest

from core.config import EMBEDDING_MODELL, Settings
from tests.regression.aehnlichkeit_paare import PAARE
from utils.text_normalisierung import ist_dasselbe, text_normalisiert

pytestmark = pytest.mark.langsam

# Wie weit ein Score von der Messung abweichen darf (CPU/Bibliotheksversion).
TOLERANZ = 0.005


@lru_cache(maxsize=1)
def _scores():
    """(qq, pp, qp) je Paar, einmal fuer alle Tests berechnet."""
    from sentence_transformers import SentenceTransformer

    modell = SentenceTransformer(EMBEDDING_MODELL)
    kandidaten = [p[3] for p in PAARE]
    bestand = [p[4] for p in PAARE]

    def einbetten(praefix, texte):
        return modell.encode(
            [f"{praefix}: {t}" for t in texte], normalize_embeddings=True
        )

    qa, pa = einbetten("query", kandidaten), einbetten("passage", kandidaten)
    qb, pb = einbetten("query", bestand), einbetten("passage", bestand)
    return {
        p[0]: (
            float(np.dot(qa[i], qb[i])),
            float(np.dot(pa[i], pb[i])),
            float(np.dot(qa[i], pb[i])),
        )
        for i, p in enumerate(PAARE)
    }


@pytest.mark.parametrize("paar", PAARE, ids=[p[0] for p in PAARE])
def test_scores_wie_gemessen(paar):
    paar_id, *_, qq, pp, qp, _gleich = paar
    assert _scores()[paar_id] == pytest.approx((qq, pp, qp), abs=TOLERANZ)


@pytest.mark.parametrize("paar", PAARE, ids=[p[0] for p in PAARE])
def test_entscheidung_der_dublettenpruefung(paar):
    """Dieselbe Regel wie StatementService.add_statement / CommentaryService."""
    paar_id, art, kategorie, kandidat, bestand, *_, gleich = paar
    settings = Settings()
    qq, pp, _ = _scores()[paar_id]
    if art == "kommentar":
        score, schwelle = pp, settings.commentary_similarity_threshold
    else:
        score, schwelle = qq, settings.statement_similarity_threshold

    entscheidung = ist_dasselbe(
        text_normalisiert(kandidat), text_normalisiert(bestand), score, schwelle
    )

    assert entscheidung is gleich
    # Die Grundregeln unabhaengig von den gespeicherten Erwartungen:
    if kategorie in "AB":
        assert entscheidung, "identisch/trivial abweichend muss als dasselbe gelten"
    if kategorie in "DE":
        assert not entscheidung, "andere Behauptung darf nie still zusammenfallen"
