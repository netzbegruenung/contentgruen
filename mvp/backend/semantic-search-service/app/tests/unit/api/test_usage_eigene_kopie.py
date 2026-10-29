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
from api.v1.usage import BeitragUnlesbar, beitrag_laden, router as usage_router
from core.config import Settings
from dependencies import get_settings

BEITRAG_ID = "11111111-1111-4111-8111-111111111111"
AUTORIN = "kim-1"
STARTKONTO = "start-9"


def einstellungen() -> Settings:
    return Settings(startkonten=STARTKONTO, punkte_aktiv=True)


@pytest.fixture
def dienst():
    """Der Usage-Service als Mock; der Zaehler steht auf 4."""
    dienst = Mock()
    dienst.track_content_usage.return_value = True
    dienst.get_content_usage.return_value = 4
    return dienst


@pytest.fixture
def client(dienst, muster):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = einstellungen

    async def beitrag_laden(content_id, settings):
        if str(content_id) != BEITRAG_ID:
            return None
        return SimpleNamespace(id=content_id, original_author=AUTORIN)

    with patch.object(
        usage_module, "get_usage_service", return_value=dienst
    ), patch.object(usage_module, "beitrag_laden", beitrag_laden), patch.object(
        usage_module, "get_muster_hinweise_service", return_value=muster
    ):
        yield TestClient(app)


@pytest.fixture
def muster():
    return Mock()


def zaehlen(client, user=None, sitzung=None):
    kopf = {"X-User": user} if user else {}
    return client.post(
        f"/api/v1/usage/content/{BEITRAG_ID}/usage",
        json={"session_id": sitzung} if sitzung else {},
        headers=kopf,
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


class TestStartkonto:
    """Ein Startkonto vergibt keine Nutzung (GLOSSARY.md "Startkonto", #352)."""

    def test_nutzung_durch_startkonto_zaehlt_nicht(self, client, dienst, muster):
        antwort = zaehlen(client, STARTKONTO)

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_not_called()
        muster.nutzung_melden.assert_not_called()


class TestEntdoppelung:
    """Fuer Punkte und "oft genutzt" zaehlt eine Nutzung je Person, Beitrag und Tag."""

    def test_angemeldete_nutzung_bekommt_pruefwert_der_person(self, client, dienst):
        zaehlen(client, "bo-2", sitzung="sitzung-1")
        zaehlen(client, "bo-2", sitzung="sitzung-2")

        erster, zweiter = [
            c.kwargs["pruefwert"] for c in dienst.track_content_usage.call_args_list
        ]
        assert erster and erster == zweiter

    def test_besucher_bekommt_pruefwert_der_sitzung(self, client, dienst):
        zaehlen(client, "anonymous", sitzung="sitzung-1")
        zaehlen(client, "anonymous", sitzung="sitzung-2")
        zaehlen(client)

        pruefwerte = [
            c.kwargs["pruefwert"] for c in dienst.track_content_usage.call_args_list
        ]
        assert pruefwerte[0] and pruefwerte[1] and pruefwerte[0] != pruefwerte[1]
        assert pruefwerte[2] is None

    def test_nutzung_wird_fuer_muster_gemeldet(self, client, muster):
        zaehlen(client, "bo-2")

        muster.nutzung_melden.assert_called_once_with("bo-2", AUTORIN)

    def test_ohne_punkte_keine_meldung_fuer_muster(self, client, muster):
        client.app.dependency_overrides[get_settings] = lambda: Settings()

        zaehlen(client, "bo-2")

        muster.nutzung_melden.assert_not_called()


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
        fabrik = Mock()
        fabrik.return_value.create_content_repository.return_value = repository

        with patch(
            "repositories.implementations.qdrant.qdrant_repository_factory.QdrantRepositoryFactory",
            fabrik,
        ):
            with pytest.raises(BeitragUnlesbar):
                asyncio.run(beitrag_laden(uuid.UUID(BEITRAG_ID), Mock()))

    def test_laden_meldet_fehlenden_als_none(self):
        repository = Mock()
        repository.get = AsyncMock(side_effect=ValueError("not found"))
        fabrik = Mock()
        fabrik.return_value.create_content_repository.return_value = repository

        with patch(
            "repositories.implementations.qdrant.qdrant_repository_factory.QdrantRepositoryFactory",
            fabrik,
        ):
            assert asyncio.run(beitrag_laden(uuid.UUID(BEITRAG_ID), Mock())) is None

    def test_unlesbarer_beitrag_zaehlt_trotzdem(self, dienst):
        """Im Zweifel zaehlen: wem er gehoert, ist dann nicht feststellbar."""
        app = FastAPI()
        app.include_router(usage_router, prefix="/api/v1/usage")
        app.dependency_overrides[get_settings] = einstellungen

        async def kaputt(content_id, settings):
            raise BeitragUnlesbar(str(content_id))

        with patch.object(
            usage_module, "get_usage_service", return_value=dienst
        ), patch.object(usage_module, "beitrag_laden", kaputt):
            client = TestClient(app)
            antwort = client.post(
                f"/api/v1/usage/content/{BEITRAG_ID}/usage",
                json={},
                headers={"X-User": AUTORIN},
            )

        assert antwort.status_code == 200
        dienst.track_content_usage.assert_called_once()
