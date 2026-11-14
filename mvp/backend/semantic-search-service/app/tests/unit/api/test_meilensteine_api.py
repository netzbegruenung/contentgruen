"""
Die eigenen Meilensteine (#351): nur mit eingeschalteten Punkten, nur fuer die
angemeldete Person selbst.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_meilensteine_service, get_settings
from domain.meilensteine import Meilenstein

URL = "/api/v1/usage/users/me/meilensteine"


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.meilensteine = AsyncMock(
        return_value=[
            Meilenstein(
                "nutzung-1",
                "Erstmals genutzt",
                "Ausgeflogen",
                "Jemand hat deinen Beitrag mitgenommen.",
                "meilensteine/vogel.svg",
                "wirkung",
                1,
                3,
            ),
            Meilenstein(
                "einwurf-1",
                "Erster Einwurf",
                "Fundstück",
                "Dein erster Einwurf liegt im Fangkorb.",
                "meilensteine/korb.svg",
                "weg",
                1,
                0,
                "Eigenes Bild, CC BY 4.0",
            ),
        ]
    )
    return dienst


def _client(dienst, aktiv: bool) -> TestClient:
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(punkte_aktiv=aktiv)
    app.dependency_overrides[get_meilensteine_service] = lambda: dienst
    return TestClient(app)


def test_eigene_meilensteine_mit_stand(dienst):
    antwort = _client(dienst, aktiv=True).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 200
    assert antwort.json() == {
        "meilensteine": [
            {
                "kennung": "nutzung-1",
                "name": "Erstmals genutzt",
                "untertitel": "Ausgeflogen",
                "beschreibung": "Jemand hat deinen Beitrag mitgenommen.",
                "bild": "meilensteine/vogel.svg",
                "bildnachweis": "Motiv: Fluent Emoji, © Microsoft Corporation, MIT-Lizenz",
                "art": "wirkung",
                "schwelle": 1,
                "stand": 3,
                "erreicht": True,
            },
            {
                "kennung": "einwurf-1",
                "name": "Erster Einwurf",
                "untertitel": "Fundstück",
                "beschreibung": "Dein erster Einwurf liegt im Fangkorb.",
                "bild": "meilensteine/korb.svg",
                "bildnachweis": "Eigenes Bild, CC BY 4.0",
                "art": "weg",
                "schwelle": 1,
                "stand": 0,
                "erreicht": False,
            },
        ]
    }
    dienst.meilensteine.assert_awaited_once_with("kim-1")


def test_eigene_meilensteine_ohne_schalter_404(dienst):
    antwort = _client(dienst, aktiv=False).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 404
    dienst.meilensteine.assert_not_called()


def test_eigene_meilensteine_nur_angemeldet(dienst):
    client = _client(dienst, aktiv=True)

    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"X-User": "anonymous"}).status_code == 401


def test_eigene_meilensteine_fehler_500(dienst):
    dienst.meilensteine.side_effect = RuntimeError("weg")

    antwort = _client(dienst, aktiv=True).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 500
