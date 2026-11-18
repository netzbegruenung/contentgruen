"""
Admin-API der Schalter (#708): nur fuer Admins, GET mit Obergrenze, Admin-Wert und
wirksam, PUT setzt den Admin-Wert, Einschalten ueber die Obergrenze hinaus 409. Die
oeffentlichen Endpunkte melden danach den wirksamen Wert.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.schalter import router as schalter_router
from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_settings
from services.schalter_service import SchalterService, schalter_service_setzen

URL = "/api/v1/moderation/schalter"
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}


@pytest.fixture
def werte():
    """Eigener Dienst ohne Eintraege: Admin-Werte gelten als aus."""
    werte = {}
    verlauf = []

    def setzen(name, an, admin):
        werte[name] = an
        verlauf.append((name, an, admin))

    schalter_service_setzen(
        SchalterService(admin_werte_lesen=lambda: dict(werte), admin_wert_setzen=setzen)
    )
    werte["_verlauf"] = verlauf
    return werte


def _client(**obergrenzen) -> TestClient:
    app = FastAPI()
    app.include_router(schalter_router, prefix=URL)
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(**obergrenzen)
    return TestClient(app)


def test_nur_fuer_admins(werte):
    client = _client(punkte_aktiv=True)

    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"X-User": "person-1"}).status_code == 403
    antwort = client.put(
        f"{URL}/punkte", json={"an": True}, headers={"X-User": "person-1"}
    )
    assert antwort.status_code == 403
    assert werte["_verlauf"] == []


def test_liste_ohne_eintrag_aus(werte):
    antwort = _client(punkte_aktiv=True).get(URL, headers=ADMIN)

    assert antwort.status_code == 200
    stand = {s["name"]: s for s in antwort.json()["schalter"]}
    assert stand["punkte"]["obergrenze"] is True
    assert stand["punkte"]["admin_wert"] is False
    assert stand["punkte"]["wirksam"] is False
    assert stand["punkte"]["umgebungsvariable"] == "SEMANTIC_SEARCH_PUNKTE_AKTIV"
    assert stand["punkte"]["erklaerung"]
    assert stand["gepostet"]["obergrenze"] is False


def test_liste_liest_frisch_ohne_cache(werte):
    client = _client(punkte_aktiv=True)
    assert client.get(URL, headers=ADMIN).status_code == 200

    werte["punkte"] = True  # andere Replika schaltet ein

    stand = {s["name"]: s for s in client.get(URL, headers=ADMIN).json()["schalter"]}
    assert stand["punkte"]["admin_wert"] is True


def test_einschalten_wirkt_auf_oeffentlichen_status(werte):
    client = _client(punkte_aktiv=True)
    assert client.get("/api/v1/usage/punkte/status").json()["aktiv"] is False

    antwort = client.put(f"{URL}/punkte", json={"an": True}, headers=ADMIN)

    assert antwort.status_code == 200
    stand = {s["name"]: s for s in antwort.json()["schalter"]}
    assert stand["punkte"]["wirksam"] is True
    assert werte["_verlauf"] == [("punkte", True, "admin-1")]
    assert client.get("/api/v1/usage/punkte/status").json()["aktiv"] is True


def test_einschalten_ueber_obergrenze_409(werte):
    antwort = _client(gepostet_aktiv=False).put(
        f"{URL}/gepostet", json={"an": True}, headers=ADMIN
    )

    assert antwort.status_code == 409
    assert "Server erlaubt" in antwort.json()["detail"]
    assert werte["_verlauf"] == []


def test_ausschalten_geht_auch_ohne_obergrenze(werte):
    antwort = _client().put(f"{URL}/gepostet", json={"an": False}, headers=ADMIN)

    assert antwort.status_code == 200
    assert werte["_verlauf"] == [("gepostet", False, "admin-1")]


def test_unbekannter_schalter_404(werte):
    antwort = _client().put(f"{URL}/gibtsnicht", json={"an": False}, headers=ADMIN)

    assert antwort.status_code == 404
