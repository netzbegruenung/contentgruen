"""
Der Schalter der Punkte, ohne Anmeldung lesbar (UX-Review B20): Das Frontend fragt
hier, statt punkte, meilensteine und abzeichen-sichtbarkeit auf ein 404 laufen zu lassen.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_settings

URL = "/api/v1/usage/punkte/status"


def _client(punkte: bool, abzeichen: bool) -> TestClient:
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings(
        punkte_aktiv=punkte, abzeichen_sichtbar_aktiv=abzeichen
    )
    return TestClient(app)


@pytest.mark.parametrize(
    "punkte, abzeichen, erwartet",
    [
        (False, False, {"aktiv": False, "abzeichen_sichtbar": False}),
        (True, False, {"aktiv": True, "abzeichen_sichtbar": False}),
        # Abzeichen nur zusammen mit den Punkten
        (False, True, {"aktiv": False, "abzeichen_sichtbar": False}),
        (True, True, {"aktiv": True, "abzeichen_sichtbar": True}),
    ],
)
def test_status_folgt_den_schaltern(punkte, abzeichen, erwartet):
    antwort = _client(punkte, abzeichen).get(URL)

    assert antwort.status_code == 200
    assert antwort.json() == erwartet


def test_status_ohne_anmeldung_und_als_besucher_lesbar():
    client = _client(True, False)

    assert client.get(URL).status_code == 200
    assert client.get(URL, headers={"X-User": "anonymous"}).status_code == 200
