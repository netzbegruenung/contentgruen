"""
Regressionstest NLI-Stufe (#387): Faellt ein Modell- oder Bibliothekswechsel auf die
Urteile am Messset, schlaegt das hier an. Laedt das NLI-Modell (~1,2 GB RAM) und den Bestaetiger (~2,2 GB); deshalb
langsam markiert und nicht in CI. Die Regel ueber die gespeicherten Urteile prueft
tests/unit/test_nli_messset.py.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m pytest tests/regression/test_nli_messset.py -m langsam -v
"""

from functools import lru_cache

import pytest

from core.config import Settings
from tests.regression.nli_messen import (
    THREADS,
    NLI_PAARE,
    bestaetigung,
    bestaetigungen_messen,
    entscheidung_nli,
    urteil,
    urteile_messen,
)

pytestmark = pytest.mark.langsam

# Wie weit eine Wahrscheinlichkeit von der Messung abweichen darf (CPU/Bibliothek).
TOLERANZ = 0.01


@lru_cache(maxsize=1)
def _urteile():
    return urteile_messen(THREADS)


@lru_cache(maxsize=1)
def _bestaetigungen():
    return bestaetigungen_messen(THREADS)


@pytest.mark.parametrize("paar", NLI_PAARE, ids=[p.id for p in NLI_PAARE])
def test_urteile_wie_gemessen(paar):
    erwartet = urteil(paar.id)
    neu = _urteile()[paar.id]
    assert [*neu.hin, *neu.rueck] == pytest.approx(
        [*erwartet.hin, *erwartet.rueck], abs=TOLERANZ
    )


@pytest.mark.parametrize("paar", NLI_PAARE, ids=[p.id for p in NLI_PAARE])
def test_entscheidung_wie_gemessen(paar):
    settings = Settings()
    assert entscheidung_nli(paar, _urteile()[paar.id], settings) is entscheidung_nli(
        paar, urteil(paar.id), settings
    )


@pytest.mark.parametrize("paar", NLI_PAARE, ids=[p.id for p in NLI_PAARE])
def test_bestaetigungen_wie_gemessen(paar):
    erwartet = bestaetigung(paar.id)
    neu = _bestaetigungen()[paar.id]
    assert [*neu.hin, *neu.rueck] == pytest.approx(
        [*erwartet.hin, *erwartet.rueck], abs=TOLERANZ
    )


@pytest.mark.parametrize("paar", NLI_PAARE, ids=[p.id for p in NLI_PAARE])
def test_entscheidung_mit_bestaetiger_wie_gemessen(paar):
    settings = Settings()
    assert entscheidung_nli(
        paar, _urteile()[paar.id], settings, _bestaetigungen()[paar.id]
    ) is entscheidung_nli(paar, urteil(paar.id), settings, bestaetigung(paar.id))
