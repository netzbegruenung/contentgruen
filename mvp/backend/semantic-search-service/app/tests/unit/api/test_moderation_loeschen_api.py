"""
DELETE /api/v1/moderation/content/{content_type}/{id}: Ein Admin entfernt einen Beitrag
endgueltig (#294).

Was das Entfernen an Beitrag und Aussagen aendert, pruefen die Service-Tests
(tests/unit/services/test_moderation_service.py); hier nur, wie der Endpunkt das
Ergebnis auf HTTP abbildet.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import moderation as moderation_module
from api.v1.moderation import router as moderation_router
from dependencies import get_settings
from services.moderation_service import VerweiseNichtEntfernt

CONTENT_ID = str(uuid.uuid4())
URL = f"/api/v1/moderation/content/generic_text/{CONTENT_ID}"
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}


@pytest.fixture
def service():
    mock = Mock()
    mock.delete_content = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    with patch.object(moderation_module, "get_moderation_service", lambda: service):
        yield TestClient(app)


@pytest.mark.unit
class TestLoeschenApi:
    def test_loeschen_admin_ist_200(self, client, service):
        antwort = client.delete(URL, headers=ADMIN)

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True

    def test_loeschen_unbekannter_beitrag_ist_404(self, client, service):
        service.delete_content.return_value = False

        assert client.delete(URL, headers=ADMIN).status_code == 404

    def test_loeschen_verweise_scheitern_ist_fehler_mit_hinweis(self, client, service):
        """Kein "ok", wenn Aussagen weiter auf den Beitrag verweisen wuerden."""
        service.delete_content.side_effect = VerweiseNichtEntfernt(CONTENT_ID)

        antwort = client.delete(URL, headers=ADMIN)

        assert antwort.status_code == 500
        hinweis = antwort.json()["detail"]
        assert "nicht gelöscht" in hinweis
        assert "erneut" in hinweis
