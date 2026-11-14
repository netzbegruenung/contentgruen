"""
Die Einwilligung "Punkte und Meilensteine" (#351): eine eigene, freiwillige
Einwilligung, nur angeboten mit eingeschalteten Punkten, nichts vorausgewaehlt,
Widerruf jederzeit und sofort wirksam.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_settings
from domain.punkte_einwilligung import AKTUELLER_WORTLAUT, WORTLAUTE
from repositories.punkte_einwilligung_repository import PunkteEinwilligung

URL = "/api/v1/usage/users/me/punkte-einwilligung"
KIM = {"X-User": "kim-1"}


def _client(aktiv: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(punkte_aktiv=aktiv)
    return TestClient(app)


@pytest.fixture
def repo(punkte_einwilligung_ohne_datenbank):
    return punkte_einwilligung_ohne_datenbank


def test_ohne_punkte_wird_nichts_angeboten():
    assert _client(aktiv=False).get(URL, headers=KIM).status_code == 404
    antwort = _client(aktiv=False).put(
        URL, headers=KIM, json={"eingewilligt": True, "wortlaut": AKTUELLER_WORTLAUT}
    )
    assert antwort.status_code == 404


def test_nur_angemeldet():
    assert _client().get(URL).status_code == 401


def test_nie_gefragt_ist_nicht_eingewilligt_und_bringt_den_wortlaut(repo):
    repo.lesen.return_value = None

    antwort = _client().get(URL, headers=KIM)

    assert antwort.status_code == 200
    assert antwort.json() == {
        "eingewilligt": False,
        "wortlaut": None,
        "aktueller_wortlaut": {
            "kennung": AKTUELLER_WORTLAUT,
            "text": WORTLAUTE[AKTUELLER_WORTLAUT],
        },
    }
    assert "Ohne diese Einwilligung kann ich genauso beitragen" in (
        antwort.json()["aktueller_wortlaut"]["text"]
    )


def test_eingewilligt_zum_geltenden_wortlaut(repo):
    repo.lesen.return_value = PunkteEinwilligung(
        True, AKTUELLER_WORTLAUT, datetime(2026, 11, 13, tzinfo=timezone.utc)
    )

    assert _client().get(URL, headers=KIM).json()["eingewilligt"] is True


def test_einwilligen_speichert_mit_wortlaut(repo):
    antwort = _client().put(
        URL, headers=KIM, json={"eingewilligt": True, "wortlaut": AKTUELLER_WORTLAUT}
    )

    assert antwort.status_code == 204
    repo.antworten.assert_called_once_with("kim-1", True, AKTUELLER_WORTLAUT)


def test_unbekannter_wortlaut_422(repo):
    antwort = _client().put(
        URL, headers=KIM, json={"eingewilligt": True, "wortlaut": "1999-01-01"}
    )

    assert antwort.status_code == 422
    repo.antworten.assert_not_called()


def test_widerruf_speichert_und_nimmt_das_abzeichen_sofort(repo, monkeypatch):
    abzeichen = MagicMock()
    monkeypatch.setattr("api.v1.usage.get_abzeichen_service", lambda: abzeichen)

    antwort = _client().put(
        URL, headers=KIM, json={"eingewilligt": False, "wortlaut": AKTUELLER_WORTLAUT}
    )

    assert antwort.status_code == 204
    repo.antworten.assert_called_once_with("kim-1", False, AKTUELLER_WORTLAUT)
    abzeichen.vergessen.assert_called_once_with("kim-1")


def test_speicherfehler_500(repo):
    repo.antworten.side_effect = RuntimeError("weg")

    antwort = _client().put(
        URL, headers=KIM, json={"eingewilligt": True, "wortlaut": AKTUELLER_WORTLAUT}
    )

    assert antwort.status_code == 500
