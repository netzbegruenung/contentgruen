"""
Die Admin-Endpunkte der Moderation ohne eigene Testdatei: Meldungen lesen,
Statistik, Beitrag endgueltig entfernen, Meldung abweisen, Meldungen einer
Person finden und ihre Angaben loeschen (Fachliches in test_moderation_melder.py). Sperren, Entsperren und die Liste
der gesperrten Beitraege prueft test_moderation_sperren.py.

Aus tests/integration/api/v1/test_moderation_api.py, dort ohne die Fixture
``client`` nie gelaufen.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.moderation import router as moderation_router
from dependencies import get_moderation_service, get_settings

MITWIRKENDE = {"X-User": "user-1", "X-Is-Admin": "false"}

# Feste Kennungen: die Test-IDs enthalten sie, pytest-xdist verlangt in jedem Worker dieselben.
ENDPUNKTE = [
    ("get", "/reports"),
    ("get", "/stats"),
    ("delete", "/content/commentary/00000000-0000-4000-8000-000000000001"),
    ("put", "/reports/00000000-0000-4000-8000-000000000002/dismiss"),
    ("post", "/melder/meldungen"),
    ("post", "/melder/angaben-loeschen"),
]


@pytest.fixture
def service():
    return Mock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_moderation_service] = lambda: service
    return TestClient(app)


@pytest.mark.api
@pytest.mark.parametrize("methode, pfad", ENDPUNKTE)
class TestNurAdmin:
    def test_mitwirkende_duerfen_nicht(self, client, service, methode, pfad):
        antwort = getattr(client, methode)(
            f"/api/v1/moderation{pfad}", headers=MITWIRKENDE
        )

        assert antwort.status_code == 403
        assert not service.method_calls

    def test_besucher_duerfen_nicht(self, client, service, methode, pfad):
        antwort = getattr(client, methode)(f"/api/v1/moderation{pfad}")

        assert antwort.status_code == 401
        assert not service.method_calls
