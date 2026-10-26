"""
DELETE /api/v1/content/{id}: Der Autor loescht seinen Beitrag (#250).

Was Loeschen am Beitrag aendert, pruefen die Service-Tests
(tests/unit/services/test_beitrag_loeschen_service.py); hier nur, wie der Endpunkt
Aufrufer und Ergebnis auf HTTP abbildet.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.content import router as content_router
from dependencies import get_beitrag_loeschen_service
from services.content.beitrag_loeschen_service import LoeschErgebnis

BEITRAG_ID = str(uuid.uuid4())


@pytest.fixture
def service():
    mock = Mock()
    mock.loeschen = AsyncMock(return_value=LoeschErgebnis.GELOESCHT)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(content_router, prefix="/api/v1/content")
    app.dependency_overrides[get_beitrag_loeschen_service] = lambda: service
    return TestClient(app)


@pytest.mark.unit
class TestBeitragLoeschenApi:
    def test_loeschen_autor_ist_204(self, client, service):
        antwort = client.delete(
            f"/api/v1/content/{BEITRAG_ID}", headers={"X-User": "autor-1"}
        )

        assert antwort.status_code == 204
        service.loeschen.assert_awaited_once_with(uuid.UUID(BEITRAG_ID), "autor-1")

    def test_loeschen_andere_person_ist_403(self, client, service):
        service.loeschen.return_value = LoeschErgebnis.NICHT_AUTOR

        antwort = client.delete(
            f"/api/v1/content/{BEITRAG_ID}", headers={"X-User": "andere"}
        )

        assert antwort.status_code == 403

    def test_loeschen_nicht_da_ist_404(self, client, service):
        service.loeschen.return_value = LoeschErgebnis.NICHT_DA

        antwort = client.delete(
            f"/api/v1/content/{BEITRAG_ID}", headers={"X-User": "autor-1"}
        )

        assert antwort.status_code == 404

    @pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
    def test_loeschen_besucher_ist_401(self, client, service, kopf):
        antwort = client.delete(f"/api/v1/content/{BEITRAG_ID}", headers=kopf)

        assert antwort.status_code == 401
        service.loeschen.assert_not_called()

    def test_loeschen_ungueltige_id_ist_422(self, client, service):
        antwort = client.delete(
            "/api/v1/content/kein-uuid", headers={"X-User": "autor-1"}
        )

        assert antwort.status_code == 422
        service.loeschen.assert_not_called()
