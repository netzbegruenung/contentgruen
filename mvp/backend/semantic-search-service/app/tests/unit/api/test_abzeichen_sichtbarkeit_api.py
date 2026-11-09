"""
Die Frage nach der Sichtbarkeit der Meilenstein-Abzeichen (#351): nur mit beiden
Schaltern, nur fuer die angemeldete Person selbst, Speichern nur mit
Art.-9-Einwilligung.
"""

import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_settings
from domain.abzeichen_sichtbarkeit import UnbekannterWortlaut
from repositories.abzeichen_sichtbarkeit_repository import Sichtbarkeit
from services import abzeichen_service as abzeichen_modul

URL = "/api/v1/usage/users/me/abzeichen-sichtbarkeit"
KIM = {"X-User": "kim-1"}


@pytest.fixture
def dienst(monkeypatch, art9_einwilligung_ohne_datenbank):
    dienst = Mock()
    dienst.sichtbarkeit = Mock(return_value=None)
    dienst.antworten = AsyncMock()
    monkeypatch.setattr(abzeichen_modul, "_service", dienst)
    return dienst


def _client(an: bool = True, punkte: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(
        punkte_aktiv=punkte, abzeichen_sichtbar_aktiv=an
    )
    return TestClient(app)


def test_nie_gefragt(dienst):
    antwort = _client().get(URL, headers=KIM)

    assert antwort.status_code == 200
    body = antwort.json()
    assert body["gefragt"] is False
    assert body["zeigen"] is None
    assert body["aktueller_wortlaut"]["kennung"] == "2026-11-09"
    dienst.sichtbarkeit.assert_called_once_with("kim-1")


def test_gefragt_mit_antwort(dienst):
    dienst.sichtbarkeit.return_value = Sichtbarkeit(
        True, "2026-11-09", datetime.datetime(2026, 11, 9)
    )

    body = _client().get(URL, headers=KIM).json()

    assert body["gefragt"] is True
    assert body["zeigen"] is True


@pytest.mark.parametrize("an,punkte", [(False, True), (True, False)])
def test_ohne_beide_schalter_404(dienst, an, punkte):
    client = _client(an=an, punkte=punkte)

    assert client.get(URL, headers=KIM).status_code == 404
    assert (
        client.put(
            URL, json={"zeigen": True, "wortlaut": "2026-11-09"}, headers=KIM
        ).status_code
        == 404
    )
    dienst.antworten.assert_not_called()


def test_nur_angemeldet(dienst):
    client = _client()

    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"X-User": "anonymous"}).status_code == 401


def test_antworten(dienst):
    antwort = _client().put(
        URL, json={"zeigen": False, "wortlaut": "2026-11-09"}, headers=KIM
    )

    assert antwort.status_code == 204
    dienst.antworten.assert_awaited_once_with("kim-1", False, "2026-11-09")


def test_antworten_unbekannter_wortlaut_422(dienst):
    dienst.antworten.side_effect = UnbekannterWortlaut("x")

    antwort = _client().put(URL, json={"zeigen": True, "wortlaut": "x"}, headers=KIM)

    assert antwort.status_code == 422


def test_nein_auch_ohne_art9_einwilligung(dienst, art9_einwilligung_ohne_datenbank):
    """Zuruecknehmen geht immer, wie der Widerruf der Einwilligung selbst."""
    art9_einwilligung_ohne_datenbank.lesen.return_value = None

    antwort = _client().put(
        URL, json={"zeigen": False, "wortlaut": "2026-11-09"}, headers=KIM
    )

    assert antwort.status_code == 204
    dienst.antworten.assert_awaited_once_with("kim-1", False, "2026-11-09")
