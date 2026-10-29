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
    assert antwort.json() == {"tun": 3, "quests": 0, "wirkung": 25, "gesamt": 28}
    dienst.punkte.assert_awaited_once_with("kim-1")


def test_eigene_punkte_ohne_schalter_404(dienst):
    antwort = _client(dienst, aktiv=False).get(URL, headers={"X-User": "kim-1"})

    assert antwort.status_code == 404
    dienst.punkte.assert_not_called()


def test_eigene_punkte_nur_angemeldet(dienst):
    client = _client(dienst, aktiv=True)

    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"X-User": "anonymous"}).status_code == 401
