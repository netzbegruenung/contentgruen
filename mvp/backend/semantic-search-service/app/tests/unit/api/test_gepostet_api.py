"""
Rueckmeldung "Gepostet?" nach dem Kopieren (#643): nur mit Schalter, nur angemeldet,
nur mit Art.-9-Einwilligung, keine Startkonten; fuer Admins die Zahl je Woche.
"""

from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.metrics import router as metrics_router
from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_settings
from services import gepostet_service as gepostet_modul
from services.gepostet_service import GepostetWoche, get_gepostet_service

URL = "/api/v1/usage/users/me/gepostet"
KIM = {"X-User": "kim-1"}
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}


@pytest.fixture
def dienst(monkeypatch, art9_einwilligung_ohne_datenbank):
    dienst = Mock()
    dienst.diese_woche.return_value = 6
    dienst.melden.return_value = 7
    monkeypatch.setattr(gepostet_modul, "_service", dienst)
    return dienst


def _client(an: bool = True, startkonten: str = "") -> TestClient:
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(
        gepostet_aktiv=an, startkonten=startkonten
    )
    return TestClient(app)


def test_melden_zaehlt_die_person_und_nennt_die_zahl(dienst):
    antwort = _client().post(URL, headers=KIM)

    assert antwort.status_code == 200
    assert antwort.json() == {"personen_diese_woche": 7}
    dienst.melden.assert_called_once_with("kim-1")


def test_stand_ohne_zu_zaehlen(dienst):
    antwort = _client().get(URL, headers=KIM)

    assert antwort.status_code == 200
    assert antwort.json() == {"personen_diese_woche": 6}
    dienst.melden.assert_not_called()


def test_ohne_schalter_404_ohne_datenbank(dienst, art9_einwilligung_ohne_datenbank):
    client = _client(an=False)

    assert client.get(URL, headers=KIM).status_code == 404
    assert client.post(URL, headers=KIM).status_code == 404
    dienst.melden.assert_not_called()
    art9_einwilligung_ohne_datenbank.lesen.assert_not_called()


@pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
def test_besucher_401(dienst, kopf):
    assert _client().post(URL, headers=kopf).status_code == 401
    dienst.melden.assert_not_called()


def test_ohne_einwilligung_403(dienst, art9_einwilligung_ohne_datenbank):
    art9_einwilligung_ohne_datenbank.lesen.return_value = None
    client = _client()

    antwort = client.post(URL, headers=KIM)

    assert antwort.status_code == 403
    assert antwort.json()["detail"] == "art9_einwilligung_fehlt"
    assert client.get(URL, headers=KIM).status_code == 403
    dienst.melden.assert_not_called()


def test_startkonto_zaehlt_nicht(dienst):
    client = _client(startkonten="kim-1")

    assert client.post(URL, headers=KIM).status_code == 404
    assert client.get(URL, headers=KIM).status_code == 404
    dienst.melden.assert_not_called()


def test_fehler_ohne_kennung_im_log(dienst, caplog):
    dienst.melden.side_effect = RuntimeError("kaputt")

    antwort = _client().post(URL, headers=KIM)

    assert antwort.status_code == 500
    assert "kim-1" not in caplog.text


def _admin_client(dienst, an: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/v1/metrics")
    app.dependency_overrides[get_settings] = lambda: Settings(gepostet_aktiv=an)
    app.dependency_overrides[get_gepostet_service] = lambda: dienst
    return TestClient(app)


def test_admin_sieht_die_zahl_je_woche():
    dienst = Mock()
    dienst.wochen.return_value = [
        GepostetWoche(date(2026, 11, 2), 3),
        GepostetWoche(date(2026, 11, 9), 0),
    ]

    antwort = _admin_client(dienst).get(
        "/api/v1/metrics/gepostet?wochen=2", headers=ADMIN
    )

    assert antwort.status_code == 200
    assert antwort.json() == {
        "aktiv": True,
        "woechentlich": [
            {"woche": "2026-11-02", "personen": 3},
            {"woche": "2026-11-09", "personen": 0},
        ],
    }
    dienst.wochen.assert_called_once_with(2)


def test_admin_ohne_schalter_leer():
    dienst = Mock()

    antwort = _admin_client(dienst, an=False).get(
        "/api/v1/metrics/gepostet", headers=ADMIN
    )

    assert antwort.json() == {"aktiv": False, "woechentlich": []}
    dienst.wochen.assert_not_called()
