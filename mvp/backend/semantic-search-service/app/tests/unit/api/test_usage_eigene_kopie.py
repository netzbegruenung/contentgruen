"""
Der Nutzungszaehler und die eigene Kopie.

Der Zaehler sagt, wie oft andere einen Beitrag brauchbar fanden. Wer den eigenen
Text kopiert, erhoeht ihn deshalb nicht. Geprueft wird das serverseitig an
``X-User``, den das BFF setzt (IdentityHeaderTransform.cs) und ein Client nicht
faelschen kann.
"""

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from dependencies import get_beitrag_laden
from services.beitrag_laden import BeitragUnlesbar, beitrag_laden

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

    async def laden(content_id):
        if str(content_id) != BEITRAG_ID:
            return None
        return SimpleNamespace(id=content_id, original_author=AUTORIN)

    app.dependency_overrides[get_beitrag_laden] = lambda: laden
    with patch.object(usage_module, "get_usage_service", return_value=dienst):
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


class TestUnlesbarerBeitrag:
    """
    Ein Datensatz, den Pydantic nicht validieren kann, ist kaputt - nicht abwesend.
    Weil ValidationError ein ValueError ist, waere er ohne eigenen Zweig als 404
    durchgegangen und die Kopie haette niemand gezaehlt.
    """

    def test_laden_meldet_unlesbar_statt_nicht_gefunden(self):
        class Winzig(BaseModel):
            zahl: int

        try:
            Winzig(zahl="keine Zahl")
        except ValidationError as echt:
            fehler = echt

        repository = Mock()
        repository.get = AsyncMock(side_effect=fehler)

        with pytest.raises(BeitragUnlesbar):
            asyncio.run(beitrag_laden(uuid.UUID(BEITRAG_ID), repository))

    def test_laden_meldet_fehlenden_als_none(self):
        repository = Mock()
        repository.get = AsyncMock(side_effect=ValueError("not found"))

        assert asyncio.run(beitrag_laden(uuid.UUID(BEITRAG_ID), repository)) is None

    def test_unlesbarer_beitrag_zaehlt_trotzdem(self, dienst):
        """Im Zweifel zaehlen: wem er gehoert, ist dann nicht feststellbar."""
        app = FastAPI()
        app.include_router(usage_router, prefix="/api/v1/usage")

        async def kaputt(content_id):
            raise BeitragUnlesbar(str(content_id))

        app.dependency_overrides[get_beitrag_laden] = lambda: kaputt
        with patch.object(usage_module, "get_usage_service", return_value=dienst):
            client = TestClient(app)
            antwort = client.post(
                f"/api/v1/usage/content/{BEITRAG_ID}/usage",
                json={},
                headers={"X-User": AUTORIN},
            )

        assert antwort.status_code == 200
        dienst.track_content_usage.assert_called_once()


class TestKeineSitzungskennung:
    """Seit #446 haelt eine Kopie keine Sitzungskennung mehr fest."""

    def test_mitgeschickte_sitzungskennung_wird_nicht_weitergegeben(
        self, client, dienst
    ):
        """Ein alter Client schickt noch session_id mit; sie wird verworfen."""
        antwort = client.post(
            f"/api/v1/usage/content/{BEITRAG_ID}/usage",
            json={"session_id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301"},
        )

        assert antwort.status_code == 200
        _, kwargs = dienst.track_content_usage.call_args
        assert "session_id" not in kwargs
