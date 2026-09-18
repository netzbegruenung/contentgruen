"""
Der Nutzungszaehler und die eigene Kopie.

Der Zaehler sagt, wie oft andere einen Beitrag brauchbar fanden. Wer den eigenen
Text kopiert, erhoeht ihn deshalb nicht. Geprueft wird das serverseitig an
``X-User``, den das BFF setzt (IdentityHeaderTransform.cs) und ein Client nicht
faelschen kann.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from dependencies import get_settings

BEITRAG_ID = "11111111-1111-4111-8111-111111111111"
AUTORIN = "kim-1"


@pytest.fixture
def dienst():
    """Der Usage-Service als Mock; der Zaehler steht auf 4."""
    dienst = Mock()
    dienst.track_content_usage.return_value = True
    dienst.get_content_usage.return_value = 4
    return dienst


@pytest.fixture
def client(dienst):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Mock()

    async def beitrag_laden(content_id, settings):
        if str(content_id) != BEITRAG_ID:
            return None
        return SimpleNamespace(id=content_id, original_author=AUTORIN)

    with patch.object(
        usage_module, "get_usage_service", return_value=dienst
    ), patch.object(usage_module, "beitrag_laden", beitrag_laden):
        yield TestClient(app)


def zaehlen(client, user=None):
    kopf = {"X-User": user} if user else {}
    return client.post(
        f"/api/v1/usage/content/{BEITRAG_ID}/usage", json={}, headers=kopf
    )


class TestEigeneKopie:
    def test_fremde_kopie_zaehlt(self, client, dienst):
        antwort = zaehlen(client, "bo-2")

        assert antwort.status_code == 200
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_called_once()

    def test_anonyme_kopie_zaehlt(self, client, dienst):
        assert zaehlen(client).status_code == 200
        assert zaehlen(client, "anonymous").status_code == 200
        assert dienst.track_content_usage.call_count == 2

    def test_eigene_kopie_zaehlt_nicht(self, client, dienst):
        antwort = zaehlen(client, AUTORIN)

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_not_called()


class TestUnbekannterBeitrag:
    def test_unbekannte_id_ist_404(self, client, dienst):
        antwort = client.post(
            "/api/v1/usage/content/22222222-2222-4222-8222-222222222222/usage",
            json={},
        )

        assert antwort.status_code == 404
        dienst.track_content_usage.assert_not_called()

    def test_kaputte_id_ist_400(self, client, dienst):
        antwort = client.post("/api/v1/usage/content/keine-uuid/usage", json={})

        assert antwort.status_code == 400
        dienst.track_content_usage.assert_not_called()
