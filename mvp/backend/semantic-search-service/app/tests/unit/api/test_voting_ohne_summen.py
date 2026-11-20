"""
Die Stimm-Schnittstelle gibt keine Summen je Beitrag heraus. Summen gehen nur mit
der Guete an der Karte hinaus, erst ab der Mindestzahl (DSFA, Massnahme M5;
services/guete_service.py). Der fruehere Endpunkt ".../stats" wurde nicht genutzt
und lieferte Summen ohne diese Schwelle; er ist entfernt.
"""

import pytest

from api.v1.voting import router as voting_router

pytestmark = pytest.mark.unit


def test_kein_endpunkt_mit_summen_je_beitrag():
    pfade = {(m, r.path) for r in voting_router.routes for m in r.methods}

    assert not any(pfad.endswith("/stats") for _, pfad in pfade)
    assert ("GET", "/content/{content_id}") in pfade
