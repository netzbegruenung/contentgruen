"""
Muster-Hinweise im Admin-Dashboard (#352): nur fuer Admins, mit Anzeigenamen.
"""

from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.metrics import router as metrics_router
from core.config import Settings
from dependencies import get_muster_hinweise_service, get_settings
from repositories.muster_hinweis_repository import MusterHinweis

URL = "/api/v1/metrics/muster-hinweise"
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.hinweise.return_value = [
        MusterHinweis("bo-2", "kim-1", 3, date(2026, 10, 20), date(2026, 10, 29))
    ]
    return dienst


def _client(dienst, aktiv: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/v1/metrics")
    app.dependency_overrides[get_settings] = lambda: Settings(punkte_aktiv=aktiv)
    app.dependency_overrides[get_muster_hinweise_service] = lambda: dienst
    return TestClient(app)


def test_muster_hinweise_mit_kennung_und_anzeigename(
    dienst, anzeigenamen_ohne_datenbank
):
    anzeigenamen_ohne_datenbank.anzeigenamen.return_value = {"kim-1": "Kim A."}

    antwort = _client(dienst).get(URL, headers=ADMIN)

    assert antwort.status_code == 200
    assert antwort.json() == {
        "aktiv": True,
        "frist_tage": 56,
        "hinweise": [
            {
                "konto_a": "bo-2",
                "name_a": None,
                "konto_b": "kim-1",
                "name_b": "Kim A.",
                "tage": 3,
                "erster_tag": "2026-10-20",
                "letzter_tag": "2026-10-29",
            }
        ],
    }


def test_muster_hinweise_ohne_punkte_aus(dienst):
    antwort = _client(dienst, aktiv=False).get(URL, headers=ADMIN)

    assert antwort.json()["aktiv"] is False
    assert antwort.json()["hinweise"] == []


def test_muster_hinweise_nur_admins(dienst):
    client = _client(dienst)

    assert client.get(URL, headers={"X-User": "kim-1"}).status_code == 403
    assert client.get(URL).status_code == 401
    dienst.hinweise.assert_not_called()
