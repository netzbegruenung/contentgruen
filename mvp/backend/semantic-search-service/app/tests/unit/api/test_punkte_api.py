"""
Der eigene Punktestand (#352): nur mit eingeschalteten Punkten, nur fuer die
angemeldete Person selbst.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_punkte_service, get_settings
from domain.punkte import Punktestand

URL = "/api/v1/usage/users/me/punkte"


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.punkte = AsyncMock(return_value=Punktestand(tun=3, quests=0, wirkung=25))
    return dienst


def _client(dienst, aktiv: bool) -> TestClient:
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(punkte_aktiv=aktiv)
    app.dependency_overrides[get_punkte_service] = lambda: dienst
    return TestClient(app)


def test_eigene_punkte_je_stufe_und_gesamt(dienst):
    antwort = _client(dienst, aktiv=True).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 200
    assert antwort.json() == {
        "tun": 3,
        "quests": 0,
        "wirkung": 25,
        "gesamt": 28,
        "sammelt": True,
    }
    dienst.punkte.assert_awaited_once_with("kim-1")


def test_eigene_punkte_sammelt_nicht(dienst):
    """Startkonto oder ohne Einwilligung: das Merkmal, damit nirgends "0 Punkte" steht."""
    dienst.punkte = AsyncMock(
        return_value=Punktestand(tun=0, quests=0, wirkung=0, sammelt=False)
    )

    antwort = _client(dienst, aktiv=True).get(URL, headers={"X-User": "start-1"})

    assert antwort.status_code == 200
    assert antwort.json()["sammelt"] is False


def test_eigene_punkte_ohne_schalter_404(dienst):
    antwort = _client(dienst, aktiv=False).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 404
    dienst.punkte.assert_not_called()


def test_eigene_punkte_nur_angemeldet(dienst):
    client = _client(dienst, aktiv=True)

    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"X-User": "anonymous"}).status_code == 401


def test_eigene_punkte_einwilligung_nicht_lesbar_500(art9_einwilligung_ohne_datenbank):
    """Ist die Art.-9-Einwilligung nicht lesbar (#559), gibt es keine Punkte, sondern 500."""
    from services.punkte_service import PunkteService

    art9_einwilligung_ohne_datenbank.lesen.side_effect = RuntimeError("weg")
    quellen = Mock()
    dienst = PunkteService(AsyncMock(return_value=[]), quellen, quellen, Settings())

    antwort = _client(dienst, aktiv=True).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 500
    quellen.get_nutzung_entdoppelt_batch.assert_not_called()
