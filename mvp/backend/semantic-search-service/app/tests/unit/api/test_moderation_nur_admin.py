"""
Die Admin-Endpunkte der Moderation ohne eigene Testdatei: Meldungen lesen,
Statistik, Beitrag endgueltig entfernen, Meldung abweisen. Sperren, Entsperren und die Liste
der gesperrten Beitraege prueft test_moderation_sperren.py.

Aus tests/integration/api/v1/test_moderation_api.py, dort ohne die Fixture
``client`` nie gelaufen.
"""

import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import moderation as moderation_module
from api.v1.moderation import router as moderation_router
from dependencies import get_settings

MITWIRKENDE = {"X-User": "user-1", "X-Is-Admin": "false"}

ENDPUNKTE = [
    ("get", "/reports"),
    ("get", "/stats"),
    ("delete", f"/content/commentary/{uuid.uuid4()}"),
    ("put", f"/reports/{uuid.uuid4()}/dismiss"),
]


@pytest.fixture
def service():
    return Mock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    with patch.object(moderation_module, "get_moderation_service", lambda: service):
        yield TestClient(app)


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
