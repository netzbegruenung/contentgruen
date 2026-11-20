"""
Bezug (services/search/bezug.py) gegen das echte Einbettungsmodell: Die Grenzen in
core/config.py sind fuer EMBEDDING_MODELL gemessen (tests/regression/SUCHTESTSET.md,
Abschnitt Bezug). Aendern sich Modell, Praefix oder Normalisierung, faellt hier auf, ob
der Befund von Produktion 0.9.0 wiederkommt oder Umformulierungen verloren gehen.
Die Unit-Tests (tests/unit/services/test_bezug.py) arbeiten nur mit gesetzten Scores.
"""

import math

import pytest

from core.config import settings

MIGRANTEN = "Migranten machen unsere Städte unsicher."


def _aehnlichkeit(manager, a: str, b: str) -> float:
    # Wie die Aussagesuche: Suchanfrage und Aussage beide mit dem Praefix "query: ",
    # Kosinus wie in Qdrant.
    va, vb = manager.encode_query(a), manager.encode_query(b)
    skalar = sum(x * y for x, y in zip(va, vb))
    return skalar / (
        math.sqrt(sum(x * x for x in va)) * math.sqrt(sum(y * y for y in vb))
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "anfrage",
    ["Open Source ist unsicher!", "Windows ist unsicher", "Ist Open Source unsicher?"],
)
async def test_fremde_anfrage_liegt_unter_der_untergrenze(
    real_embeddings_manager, anfrage
):
    assert (
        _aehnlichkeit(real_embeddings_manager, anfrage, MIGRANTEN)
        < settings.suche_bezug_ab
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "anfrage",
    [
        "Ausländer machen unsere Städte unsicher",
        "Wegen der Migranten ist es in unseren Städten gefährlich",
    ],
)
async def test_umformulierung_liegt_ueber_sicher_ab(real_embeddings_manager, anfrage):
    assert (
        _aehnlichkeit(real_embeddings_manager, anfrage, MIGRANTEN)
        >= settings.suche_bezug_sicher_ab
    )
